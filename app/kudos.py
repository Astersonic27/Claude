"""Kudos API: give kudos, public feed, and admin moderation."""
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, render_template, request, session

from .auth import admin_required, login_required
from .db import get_db

bp = Blueprint("kudos", __name__)

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _clean(text) -> str:
    """Trim, strip control characters, collapse runs of blank lines."""
    text = _CONTROL.sub("", str(text or "")).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _public(row, admin: bool = False) -> dict:
    out = {
        "id": row["id"],
        "sender": {"id": row["sender_id"], "name": row["sender_name"]},
        "recipient": {"id": row["recipient_id"], "name": row["recipient_name"]},
        "message": row["message"],
        "created_at": row["created_at"],
    }
    if admin:
        out.update(is_visible=bool(row["is_visible"]), moderated_by=row["moderated_by"],
                   moderated_at=row["moderated_at"], moderation_reason=row["moderation_reason"])
    return out


_SELECT = """
    SELECT k.*, s.display_name AS sender_name, r.display_name AS recipient_name
    FROM kudos k
    JOIN users s ON s.id = k.sender_id
    JOIN users r ON r.id = k.recipient_id
"""


@bp.route("/")
@login_required
def dashboard(user):
    return render_template("dashboard.html", user=user, csrf=session["csrf"])


@bp.get("/api/users")
@login_required
def list_users(user):
    rows = get_db().execute(
        "SELECT id, display_name FROM users WHERE is_active = 1 AND id <> ? ORDER BY display_name", (user["id"],)
    ).fetchall()
    return jsonify(users=[{"id": r["id"], "name": r["display_name"]} for r in rows])


@bp.post("/api/kudos")
@login_required
def create_kudos(user):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="JSON body required"), 400

    errors = {}
    recipient_id = data.get("recipient_id")
    if not isinstance(recipient_id, int) or isinstance(recipient_id, bool):
        errors["recipient_id"] = "Select a colleague."
    elif recipient_id == user["id"]:
        errors["recipient_id"] = "You cannot give kudos to yourself."
    message = _clean(data.get("message"))
    max_len = current_app.config["MESSAGE_MAX_LEN"]
    if not message:
        errors["message"] = "Message is required."
    elif len(message) > max_len:
        errors["message"] = f"Message must be at most {max_len} characters."
    if errors:
        return jsonify(error="validation failed", fields=errors), 422

    db = get_db()
    if not db.execute("SELECT 1 FROM users WHERE id = ? AND is_active = 1", (recipient_id,)).fetchone():
        return jsonify(error="validation failed", fields={"recipient_id": "Unknown colleague."}), 422

    now = datetime.now(timezone.utc)
    # Spam control: per-sender hourly limit.
    limit = current_app.config["RATE_LIMIT_PER_HOUR"]
    recent = db.execute("SELECT COUNT(*) FROM kudos WHERE sender_id = ? AND created_at > ?",
                        (user["id"], _iso(now - timedelta(hours=1)))).fetchone()[0]
    if recent >= limit:
        return jsonify(error=f"Limit of {limit} kudos per hour reached. Please try again later."), 429
    # Duplicate control: same sender + recipient + message inside the window.
    window = current_app.config["DUPLICATE_WINDOW_HOURS"]
    dup = db.execute(
        "SELECT 1 FROM kudos WHERE sender_id = ? AND recipient_id = ? AND lower(message) = lower(?) AND created_at > ?",
        (user["id"], recipient_id, message, _iso(now - timedelta(hours=window))),
    ).fetchone()
    if dup:
        return jsonify(error="You already sent this exact message to this colleague recently."), 409

    try:
        cur = db.execute("INSERT INTO kudos (sender_id, recipient_id, message, created_at) VALUES (?,?,?,?)",
                         (user["id"], recipient_id, message, _iso(now)))
        db.commit()
    except sqlite3.Error:
        current_app.logger.exception("failed to insert kudos")
        return jsonify(error="could not save kudos"), 500
    current_app.logger.info("kudos %s: user %s -> user %s", cur.lastrowid, user["id"], recipient_id)
    row = db.execute(_SELECT + " WHERE k.id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(kudos=_public(row)), 201


@bp.get("/api/kudos")
@login_required
def feed(user):
    """Public feed: visible kudos only, newest first, cursor pagination (before_id)."""
    size = current_app.config["FEED_PAGE_SIZE"]
    try:
        limit = max(1, min(int(request.args.get("limit", size)), 50))
        before = int(request.args["before_id"]) if "before_id" in request.args else None
    except ValueError:
        return jsonify(error="limit and before_id must be integers"), 400
    sql, args = _SELECT + " WHERE k.is_visible = 1", []
    if before is not None:
        sql += " AND k.id < ?"; args.append(before)
    rows = get_db().execute(sql + " ORDER BY k.id DESC LIMIT ?", (*args, limit + 1)).fetchall()
    page = rows[:limit]
    return jsonify(kudos=[_public(r) for r in page], next_before_id=page[-1]["id"] if len(rows) > limit else None)


# ---------------------------------------------------------------- moderation
@bp.get("/api/admin/kudos")
@admin_required
def admin_list(user):
    status = request.args.get("status", "all")
    where = {"all": "", "hidden": " WHERE k.is_visible = 0", "visible": " WHERE k.is_visible = 1"}.get(status)
    if where is None:
        return jsonify(error="status must be all, hidden or visible"), 400
    rows = get_db().execute(_SELECT + where + " ORDER BY k.id DESC LIMIT 100").fetchall()
    return jsonify(kudos=[_public(r, admin=True) for r in rows])


def _moderate(user, kudos_id: int, action: str):
    data = request.get_json(silent=True) or {}
    reason = _clean(data.get("reason"))[:300] or None
    db = get_db()
    row = db.execute("SELECT * FROM kudos WHERE id = ?", (kudos_id,)).fetchone()
    if row is None:
        return jsonify(error="kudos not found"), 404
    now = _iso(datetime.now(timezone.utc))
    if action == "delete":
        db.execute("DELETE FROM kudos WHERE id = ?", (kudos_id,))
    else:
        visible = 1 if action == "unhide" else 0
        db.execute("UPDATE kudos SET is_visible = ?, moderated_by = ?, moderated_at = ?, moderation_reason = ? WHERE id = ?",
                   (visible, user["id"], now, reason, kudos_id))
    db.execute("INSERT INTO moderation_log (kudos_id, admin_id, action, reason, message, created_at) VALUES (?,?,?,?,?,?)",
               (kudos_id, user["id"], action, reason, row["message"], now))
    db.commit()
    current_app.logger.info("moderation: admin %s %s kudos %s", user["id"], action, kudos_id)
    return jsonify(ok=True, id=kudos_id, action=action)


@bp.post("/api/admin/kudos/<int:kudos_id>/hide")
@admin_required
def hide(user, kudos_id):
    return _moderate(user, kudos_id, "hide")


@bp.post("/api/admin/kudos/<int:kudos_id>/unhide")
@admin_required
def unhide(user, kudos_id):
    return _moderate(user, kudos_id, "unhide")


@bp.delete("/api/admin/kudos/<int:kudos_id>")
@admin_required
def delete(user, kudos_id):
    return _moderate(user, kudos_id, "delete")
