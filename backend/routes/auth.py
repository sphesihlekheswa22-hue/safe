"""Authentication endpoints: register, login, current user, logout.

Security notes:
- Passwords are bcrypt-hashed; plaintext is never stored.
- Self-registration ALWAYS creates a PUBLIC_USER. The client cannot pick a
  role; any "role" field in the payload is ignored. Only SYSTEM_ADMIN can
  change roles (see routes/admin.py).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from extensions import db
from models.user import User
from utils.rbac import Role, current_user
from utils.security import (
    hash_password,
    verify_password,
    is_strong_password,
    normalize_email,
    clean_str,
)
from middleware.rate_limit import rate_limit
from services import notification_service, settings_service

bp = Blueprint("auth", __name__)


@bp.post("/register")
@rate_limit(max_requests=10, window_seconds=60)
def register():
    data = request.get_json(silent=True) or {}

    # Admin can close public self-registration from the security panel.
    if not settings_service.get("registration_open", True):
        return jsonify(error="Public registration is currently closed. Please contact an administrator."), 403

    name = clean_str(data.get("name"), 120)
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""

    if not name:
        return jsonify(error="Name is required."), 400
    if not email:
        return jsonify(error="A valid email address is required."), 400
    if not is_strong_password(password):
        return (
            jsonify(error="Password must be at least 8 characters and include a letter and a number."),
            400,
        )

    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with that email already exists."), 409

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        # Role is forced server-side. Client input is ignored entirely.
        role=Role.PUBLIC_USER,
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return (
        jsonify(
            message="Registration successful.",
            access_token=token,
            user=user.to_dict(),
        ),
        201,
    )


@bp.post("/login")
@rate_limit(max_requests=10, window_seconds=60)
def login():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(error="Email and password are required."), 400

    user = User.query.filter_by(email=email).first()
    # Use the same generic message to avoid leaking which field was wrong.
    if user is None or not verify_password(user.password_hash, password):
        return jsonify(error="Invalid email or password."), 401
    if not user.is_active:
        return jsonify(error="This account has been disabled."), 403

    token = create_access_token(identity=str(user.id))
    # Record the login so the admin System Monitoring panel can report activity.
    notification_service.record_audit(user, "user.login", target=user.email)
    return jsonify(
        message="Login successful.",
        access_token=token,
        user=user.to_dict(),
    )


@bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if user is None:
        return jsonify(error="User not found."), 404
    return jsonify(user=user.to_dict())


@bp.put("/profile")
@jwt_required()
def update_profile():
    user = current_user()
    if user is None:
        return jsonify(error="User not found."), 404

    data = request.get_json(silent=True) or {}
    name = clean_str(data.get("name"), 120)
    if not name:
        return jsonify(error="Name is required."), 400

    user.name = name
    db.session.commit()
    return jsonify(message="Profile updated.", user=user.to_dict())


@bp.put("/password")
@jwt_required()
def change_password():
    user = current_user()
    if user is None:
        return jsonify(error="User not found."), 404

    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_pw = data.get("new_password") or ""

    if not current or not new_pw:
        return jsonify(error="Current and new password are required."), 400
    if not verify_password(user.password_hash, current):
        return jsonify(error="Current password is incorrect."), 401
    if not is_strong_password(new_pw):
        return (
            jsonify(error="Password must be at least 8 characters and include a letter and a number."),
            400,
        )

    user.password_hash = hash_password(new_pw)
    db.session.commit()
    notification_service.record_audit(user, "user.password_changed", target=user.email)
    return jsonify(message="Password updated.")


@bp.post("/logout")
@jwt_required()
def logout():
    # Stateless JWT: the client discards the token. Endpoint exists so the
    # frontend has a single, explicit logout call to make.
    return jsonify(message="Logged out. Please discard your access token.")
