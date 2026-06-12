"""Administration endpoints: user management (SYSTEM_ADMIN only).

This is the ONLY place a user's role can be changed, enforcing the rule that
users can never pick their own role. Every privileged action is audit-logged.
"""
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from sqlalchemy import text

from extensions import db
from models.user import User
from models.audit_log import AuditLog
from models.event import Event
from models.route import Route
from models.risk import RiskArea
from schemas.user_schema import validate_role_assignment
from services import notification_service, settings_service
from utils.validators import ValidationError
from utils.security import hash_password, normalize_email, is_strong_password, clean_str
from repositories import user_repo
from middleware.rbac_middleware import require_permission, current_user, PERMISSION_MATRIX
from utils.rbac import Role

bp = Blueprint("admin", __name__)


@bp.get("/users")
@require_permission("user:manage")
def list_users():
    users = user_repo.list_all()
    return jsonify(users=[u.to_dict() for u in users])


@bp.get("/roles")
@require_permission("user:manage")
def list_roles():
    return jsonify(roles=Role.all())


@bp.put("/users/<int:user_id>/role")
@require_permission("user:manage")
def assign_role(user_id):
    user = user_repo.get(user_id)
    if user is None:
        return jsonify(error="User not found."), 404

    try:
        payload = validate_role_assignment(request.get_json(silent=True) or {})
    except ValidationError as e:
        body = e.to_dict()
        body["valid_roles"] = Role.all()
        return jsonify(body), 400

    old_role = user.role
    user.role = payload["role"]
    user_repo.save()
    notification_service.record_audit(
        current_user(), "user.role_changed", target=user.email,
        detail=f"{old_role} -> {user.role}",
    )
    return jsonify(message="Role updated.", user=user.to_dict())


@bp.put("/users/<int:user_id>/status")
@require_permission("user:manage")
def set_status(user_id):
    user = user_repo.get(user_id)
    if user is None:
        return jsonify(error="User not found."), 404

    me = current_user()
    if me and me.id == user.id:
        return jsonify(error="You cannot change your own active status."), 400

    data = request.get_json(silent=True) or {}
    user.is_active = bool(data.get("is_active", True))
    user_repo.save()
    notification_service.record_audit(
        me, "user.status_changed", target=user.email,
        detail=f"is_active={user.is_active}",
    )
    return jsonify(message="Status updated.", user=user.to_dict())


@bp.delete("/users/<int:user_id>")
@require_permission("user:manage")
def delete_user(user_id):
    user = user_repo.get(user_id)
    if user is None:
        return jsonify(error="User not found."), 404

    me = current_user()
    if me and me.id == user.id:
        return jsonify(error="You cannot delete your own account."), 400

    email = user.email
    user_repo.delete(user)
    notification_service.record_audit(me, "user.deleted", target=email)
    return jsonify(message="User deleted.")


@bp.post("/users")
@require_permission("user:manage")
def create_user():
    """Admin-created accounts. Unlike public registration, the admin chooses the role."""
    data = request.get_json(silent=True) or {}
    name = clean_str(data.get("name"), 120)
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""
    role = (data.get("role") or Role.PUBLIC_USER).upper()

    if not name:
        return jsonify(error="Name is required."), 400
    if not email:
        return jsonify(error="A valid email address is required."), 400
    if not is_strong_password(password):
        return jsonify(error="Password must be at least 8 characters and include a letter and a number."), 400
    if not Role.is_valid(role):
        return jsonify(error="Invalid role.", valid_roles=Role.all()), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with that email already exists."), 409

    user = User(
        name=name, email=email, role=role,
        password_hash=hash_password(password),
    )
    db.session.add(user)
    db.session.commit()
    notification_service.record_audit(
        current_user(), "user.created", target=email, detail=f"role={role}"
    )
    return jsonify(message="User created.", user=user.to_dict()), 201


@bp.put("/users/<int:user_id>/password")
@require_permission("user:manage")
def reset_password(user_id):
    user = user_repo.get(user_id)
    if user is None:
        return jsonify(error="User not found."), 404

    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""
    if not is_strong_password(password):
        return jsonify(error="Password must be at least 8 characters and include a letter and a number."), 400

    user.password_hash = hash_password(password)
    user_repo.save()
    notification_service.record_audit(current_user(), "user.password_reset", target=user.email)
    return jsonify(message="Password reset.")


@bp.get("/audit")
@require_permission("user:manage")
def audit_log():
    action = request.args.get("action")
    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action.like(f"%{action}%"))
    logs = q.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(audit=[a.to_dict() for a in logs])


# ---------------------------------------------------------------------------
# System monitoring
# ---------------------------------------------------------------------------
@bp.get("/system")
@require_permission("user:manage")
def system_status():
    # Database health
    db_status = "up"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    since = datetime.utcnow() - timedelta(hours=24)
    recent_logins = AuditLog.query.filter(
        AuditLog.action == "user.login", AuditLog.created_at >= since
    ).count()

    return jsonify(
        status="operational" if db_status == "up" else "degraded",
        services={
            "api": "ok",
            "database": db_status,
            "risk_engine": "enabled" if settings_service.get("risk_engine_enabled", True) else "disabled",
            "ai_model": settings_service.get("ai_model", "rule_based"),
        },
        counts={
            "users": User.query.count(),
            "active_users": User.query.filter_by(is_active=True).count(),
            "events": Event.query.count(),
            "routes": Route.query.count(),
            "risk_areas": RiskArea.query.count(),
        },
        recent_logins_24h=recent_logins,
        server_time=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Settings (AI model control + security control)
# ---------------------------------------------------------------------------
@bp.get("/settings")
@require_permission("user:manage")
def get_settings():
    return jsonify(
        settings=settings_service.get_all(),
        permission_matrix={cap: roles for cap, roles in PERMISSION_MATRIX.items()},
    )


@bp.put("/settings")
@require_permission("user:manage")
def update_settings():
    data = request.get_json(silent=True) or {}
    updated = settings_service.set_many(data)
    if not updated:
        return jsonify(error="No valid settings provided."), 400
    notification_service.record_audit(
        current_user(), "system.settings_updated",
        detail=", ".join(f"{k}={v}" for k, v in updated.items()),
    )
    return jsonify(message="Settings updated.", updated=updated, settings=settings_service.get_all())


# ---------------------------------------------------------------------------
# Emergency broadcast (creates a high-severity event)
# ---------------------------------------------------------------------------
@bp.post("/broadcast")
@require_permission("user:manage")
def emergency_broadcast():
    from services import ingestion_service as ingestion

    data = request.get_json(silent=True) or {}
    message = clean_str(data.get("message"), 1000)
    location = clean_str(data.get("location"), 255) or "City-wide"

    if not message:
        return jsonify(error="Broadcast message is required."), 400

    try:
        severity = max(1, min(5, int(data.get("severity", 5))))
    except (TypeError, ValueError):
        severity = 5

    me = current_user()
    event = ingestion.ingest_event(
        title=message[:200],
        location=location,
        severity=severity,
        description=message,
        source="emergency_broadcast",
        created_by=me.id if me else None,
    )
    notification_service.record_audit(
        me, "system.emergency_broadcast", target=location,
        detail=f"severity={severity}, event_id={event.id}",
    )
    return jsonify(message="Emergency incident broadcast created.", event=event.to_dict()), 201
