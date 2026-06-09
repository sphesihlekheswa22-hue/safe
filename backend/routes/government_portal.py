"""Government Authority portal — city-wide safety command centre."""
from flask import Blueprint, request, jsonify, Response
import json

from models.alert import Alert
from services import government_service, notification_service
from schemas.alert_schema import validate_create
from utils.validators import ValidationError
from repositories import alert_repo
from middleware.rbac_middleware import require_permission, current_user

bp = Blueprint("government_portal", __name__)


def _portal_user():
    user = current_user()
    if user.role not in ("GOVERNMENT_AUTHORITY", "SYSTEM_ADMIN"):
        return None, (jsonify(error="Government portal is for Government Authorities only."), 403)
    return user, None


@bp.get("/dashboard")
@require_permission("government:portal")
def dashboard():
    user, err = _portal_user()
    if err:
        return err
    try:
        return jsonify(government_service.dashboard_payload(user))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/map-data")
@require_permission("government:portal")
def map_data():
    user, err = _portal_user()
    if err:
        return err
    return jsonify(government_service.map_payload(user))


@bp.get("/reports")
@require_permission("government:portal")
def reports():
    user, err = _portal_user()
    if err:
        return err
    return jsonify(report=government_service.city_safety_report())


@bp.get("/reports/download")
@require_permission("government:portal")
def reports_download():
    user, err = _portal_user()
    if err:
        return err
    report = government_service.city_safety_report()
    body = json.dumps(report, indent=2)
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=saferoute-city-safety-report.json"},
    )


@bp.post("/warnings")
@require_permission("government:issue_warning")
def issue_warning():
    """Issue an official public safety warning to the city."""
    user, err = _portal_user()
    if err:
        return err
    try:
        data = validate_create(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    # Government warnings default to city-wide unless a specific role is set
    if not request.get_json(silent=True).get("target_role"):
        data["target_role"] = "ALL"

    alert = Alert(
        message=data["message"],
        severity=data["severity"],
        target_role=data["target_role"],
        created_by=user.id,
    )
    alert_repo.add(alert)
    notification_service.dispatch_alert(alert)
    notification_service.record_audit(user, "government.warning_issued", target=f"alert#{alert.id}")
    return jsonify(message="Public safety warning issued.", alert=alert.to_dict()), 201
