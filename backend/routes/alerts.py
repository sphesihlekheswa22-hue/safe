"""Alerts CRUD API. Reads are scoped by role; writes require an authority/admin
role. New alerts are dispatched through the notification service."""
from flask import Blueprint, request, jsonify

from models.alert import Alert
from schemas.alert_schema import validate_create
from utils.validators import ValidationError
from repositories import alert_repo
from services import notification_service
from middleware.rbac_middleware import require_permission, current_user
from utils.rbac import Role

bp = Blueprint("alerts", __name__)

_SEE_ALL_ROLES = (Role.SYSTEM_ADMIN, Role.SYSTEM_ANALYST)


@bp.get("")
@require_permission("alert:read")
def list_alerts():
    user = current_user()
    see_all = user.role in _SEE_ALL_ROLES
    alerts = alert_repo.list_for_role(user.role, see_all=see_all)
    return jsonify(alerts=[a.to_dict() for a in alerts])


@bp.post("")
@require_permission("alert:write")
def create_alert():
    try:
        data = validate_create(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    user = current_user()
    alert = Alert(
        message=data["message"],
        severity=data["severity"],
        target_role=data["target_role"],
        created_by=user.id if user else None,
    )
    alert_repo.add(alert)
    notification_service.dispatch_alert(alert)
    notification_service.record_audit(user, "alert.created", target=f"alert#{alert.id}")
    return jsonify(message="Alert created.", alert=alert.to_dict()), 201


@bp.delete("/<int:alert_id>")
@require_permission("alert:write")
def delete_alert(alert_id):
    alert = alert_repo.get(alert_id)
    if alert is None:
        return jsonify(error="Alert not found."), 404
    alert_repo.delete(alert)
    return jsonify(message="Alert deleted.")
