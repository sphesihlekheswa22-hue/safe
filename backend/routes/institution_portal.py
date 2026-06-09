"""Institution Admin portal API — scoped dashboard, map, reports, profile."""
from flask import Blueprint, request, jsonify, Response
import json

from extensions import db
from models.institution import Institution
from services import institution_service, notification_service
from services.institution_service import require_institution
from middleware.rbac_middleware import require_permission, current_user
from utils.security import clean_str
from utils.constants import INSTITUTION_TYPES

bp = Blueprint("institution_portal", __name__)


def _portal_user():
    user = current_user()
    if user.role not in ("INSTITUTION_ADMIN", "SYSTEM_ADMIN"):
        return None, (jsonify(error="Institution portal is for Institution Admins only."), 403)
    if user.role == "SYSTEM_ADMIN" and not user.institution_id:
        return None, (jsonify(error="Link your admin account to an institution to preview the portal."), 400)
    return user, None


@bp.get("/dashboard")
@require_permission("institution:portal")
def dashboard():
    user, err = _portal_user()
    if err:
        return err
    try:
        return jsonify(institution_service.dashboard_payload(user))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/map-data")
@require_permission("institution:portal")
def map_data():
    user, err = _portal_user()
    if err:
        return err
    try:
        return jsonify(institution_service.map_payload(user))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/reports")
@require_permission("institution:portal")
def reports():
    user, err = _portal_user()
    if err:
        return err
    try:
        inst = require_institution(user)
        return jsonify(report=institution_service.build_report(inst))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/reports/download")
@require_permission("institution:portal")
def reports_download():
    user, err = _portal_user()
    if err:
        return err
    try:
        inst = require_institution(user)
        report = institution_service.build_report(inst)
        body = json.dumps(report, indent=2)
        filename = f"saferoute-{inst.name.replace(' ', '-').lower()}-report.json"
        return Response(
            body,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/profile")
@require_permission("institution:portal")
def get_profile():
    user, err = _portal_user()
    if err:
        return err
    try:
        inst = require_institution(user)
        institution_service.sync_institution_coords(inst)
        db.session.commit()
        return jsonify(institution=inst.to_dict(), user=user.to_dict())
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.put("/profile")
@require_permission("institution:manage_own")
def update_profile():
    user, err = _portal_user()
    if err:
        return err
    try:
        inst = require_institution(user)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    data = request.get_json(silent=True) or {}
    if "location" in data:
        inst.location = clean_str(data.get("location"), 255)
    if "type" in data:
        type_ = (clean_str(data.get("type"), 80) or "GENERIC").upper()
        if type_ in INSTITUTION_TYPES:
            inst.type = type_
    if "staff_count" in data:
        try:
            inst.staff_count = max(0, int(data.get("staff_count", 0)))
        except (TypeError, ValueError):
            return jsonify(error="staff_count must be an integer."), 400
    if "student_count" in data:
        try:
            inst.student_count = max(0, int(data.get("student_count", 0)))
        except (TypeError, ValueError):
            return jsonify(error="student_count must be an integer."), 400
    if "radius_km" in data:
        try:
            inst.radius_km = max(1.0, min(25.0, float(data.get("radius_km", 8))))
        except (TypeError, ValueError):
            return jsonify(error="radius_km must be a number."), 400

    institution_service.sync_institution_coords(inst)
    db.session.commit()
    notification_service.record_audit(user, "institution.profile_updated", target=inst.name)
    return jsonify(message="Institution profile updated.", institution=inst.to_dict())
