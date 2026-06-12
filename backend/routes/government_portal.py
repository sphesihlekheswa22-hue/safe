"""Government Authority portal — city-wide safety command centre."""
from flask import Blueprint, request, jsonify, Response
import json

from services import government_service, ingestion_service, notification_service
from utils.validators import ValidationError, require
from utils.security import clean_str
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
    """Issue an official public safety warning as a tracked event."""
    user, err = _portal_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        require(data, "message", "location")
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    message = clean_str(data.get("message"), 1000)
    location = clean_str(data.get("location"), 255)
    if not message or not location:
        return jsonify(error="Message and location are required."), 400

    try:
        severity = max(1, min(5, int(data.get("severity", 4))))
    except (TypeError, ValueError):
        severity = 4

    event = ingestion_service.ingest_event(
        title=message[:200],
        location=location,
        severity=severity,
        description=message,
        source="government_warning",
        created_by=user.id,
    )
    notification_service.record_audit(
        user, "government.warning_issued", target=f"event#{event.id}",
    )
    return jsonify(message="Public safety warning recorded as incident.", event=event.to_dict()), 201
