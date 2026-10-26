"""Kudos system - Flask application factory."""
import logging
import os
import secrets

from flask import Flask, jsonify, request, session

from . import auth, db, kudos


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.path.join(app.instance_path, "kudos.sqlite"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=16 * 1024,     # reject oversized request bodies
        MESSAGE_MAX_LEN=500,
        RATE_LIMIT_PER_HOUR=5,            # kudos per sender per hour
        DUPLICATE_WINDOW_HOURS=24,        # identical sender+recipient+message
        FEED_PAGE_SIZE=20,
    )
    if config:
        app.config.update(config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db.init_db(app)
    app.teardown_appcontext(db.close_db)
    app.register_blueprint(auth.bp)
    app.register_blueprint(kudos.bp)

    @app.before_request
    def csrf_protect():
        """State-changing requests must carry the session's CSRF token."""
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.endpoint != "auth.login":
            token = session.get("csrf")
            if not token or not secrets.compare_digest(token, request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")):
                return jsonify(error="invalid or missing CSRF token"), 403

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="not found"), 404

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify(error="request too large"), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("unhandled error: %s", e)
        return jsonify(error="internal server error"), 500

    return app
