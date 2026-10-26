"""Authentication (session based) and authorization helpers."""
import functools
import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)


def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute(
        "SELECT id, username, display_name, is_admin FROM users WHERE id = ? AND is_active = 1", (uid,)
    ).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        user = current_user()
        if user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("auth.login"))
        return view(user, *a, **kw)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(user, *a, **kw):
        if not user["is_admin"]:
            return jsonify(error="administrator access required"), 403
        return view(user, *a, **kw)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        row = get_db().execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (request.form.get("username", "").strip(),),
        ).fetchone()
        if row and check_password_hash(row["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = row["id"]
            session["csrf"] = secrets.token_urlsafe(32)
            return redirect(url_for("kudos.dashboard"))
        error = "Invalid username or password."   # same message for both cases
    return render_template("login.html", error=error), (401 if error else 200)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
