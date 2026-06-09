"""Authentication helpers and request hooks."""
from flask import g, request
from flask_jwt_extended import verify_jwt_in_request

from extensions import db
from utils.rbac import current_user


def load_user_into_g():
    """Optional before_request hook: attach the user to ``g`` if a valid JWT is
    present. Never blocks the request - protected routes still use decorators.
    """
    g.current_user = None
    if request.path.startswith("/api/") and "Authorization" in request.headers:
        try:
            verify_jwt_in_request(optional=True)
            g.current_user = current_user()
        except Exception:
            db.session.rollback()
            g.current_user = None


def register(app):
    app.before_request(load_user_into_g)
