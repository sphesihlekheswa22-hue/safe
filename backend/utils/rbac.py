"""Role definitions and server-side Role Based Access Control.

Roles are NEVER trusted from the client. The ``require_roles`` decorator loads
the authenticated user from the database (via the JWT identity) and checks the
persisted role column. There is no way to elevate privileges from the frontend.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


class Role:
    """Canonical role names. Use these constants everywhere."""

    PUBLIC_USER = "PUBLIC_USER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

    @classmethod
    def all(cls):
        return [cls.PUBLIC_USER, cls.SYSTEM_ADMIN]

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.all()


def current_user():
    """Return the User row referenced by the current JWT, or ``None``.

    Imported lazily to avoid a circular import (models import nothing from here,
    but this keeps the dependency direction clean).
    """
    from extensions import db
    from models.user import User

    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    try:
        return db.session.get(User, user_id)
    except Exception:
        db.session.rollback()
        return None


def require_roles(*allowed_roles):
    """Decorator enforcing JWT auth + role membership on a view.

    Usage::

        @bp.get("/secret")
        @require_roles(Role.SYSTEM_ADMIN)
        def secret():
            ...

    Returns 401 when the token is missing/invalid and 403 when the
    authenticated user's persisted role is not in ``allowed_roles``.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            # Raises/returns a 401 automatically if the JWT is missing/invalid.
            verify_jwt_in_request()

            user = current_user()
            if user is None:
                return jsonify(error="Authentication required."), 401
            if not user.is_active:
                return jsonify(error="Account is disabled."), 403
            if allowed_roles and user.role not in allowed_roles:
                return (
                    jsonify(
                        error="You do not have permission to access this resource.",
                        required_roles=list(allowed_roles),
                        your_role=user.role,
                    ),
                    403,
                )
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
