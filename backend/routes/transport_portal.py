"""Transport Operator portal API — route safety, fleet, rerouting."""
from flask import Blueprint, request, jsonify

from models.route import Route
from services import transport_service, geocoding_service
from services.geocoding_service import GeocodeError
from services.transport_service import require_transport_operator
from schemas.route_schema import validate_generate
from repositories import route_repo
from middleware.rbac_middleware import require_permission, current_user
from utils.validators import ValidationError

bp = Blueprint("transport_portal", __name__)


def _portal_user():
    user = current_user()
    if user.role not in ("TRANSPORT_OPERATOR", "SYSTEM_ADMIN"):
        return None, (jsonify(error="Transport portal is for Transport Operators only."), 403)
    if user.role == "SYSTEM_ADMIN" and not user.institution_id:
        return None, (jsonify(error="Link your account to a transport company to preview the portal."), 400)
    return user, None


@bp.get("/dashboard")
@require_permission("transport:portal")
def dashboard():
    user, err = _portal_user()
    if err:
        return err
    try:
        return jsonify(transport_service.dashboard_payload(user))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.get("/map-data")
@require_permission("transport:portal")
def map_data():
    user, err = _portal_user()
    if err:
        return err
    try:
        return jsonify(transport_service.map_payload(user))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.post("/suggest-route")
@require_permission("transport:portal")
def suggest_route():
    user, err = _portal_user()
    if err:
        return err
    try:
        data = validate_generate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400
    try:
        result = transport_service.suggest_route(
            data["start_location"], data["end_location"],
            data.get("start_lat"), data.get("start_lng"),
            data.get("end_lat"), data.get("end_lng"),
        )
        return jsonify(result), 200
    except GeocodeError as e:
        return jsonify(error=str(e)), 400


@bp.post("/routes")
@require_permission("transport:manage_routes")
def save_route():
    """Save a suggested route as an active transport route."""
    user, err = _portal_user()
    if err:
        return err
    try:
        data = validate_generate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400
    try:
        result = transport_service.suggest_route(
            data["start_location"], data["end_location"],
            data.get("start_lat"), data.get("start_lng"),
            data.get("end_lat"), data.get("end_lng"),
        )
        r = result["route"]
        route = Route(
            start_location=r["start_location"],
            end_location=r["end_location"],
            start_lat=r.get("start_lat"),
            start_lng=r.get("start_lng"),
            end_lat=r.get("end_lat"),
            end_lng=r.get("end_lng"),
            risk_score=r["risk_score"],
            geojson=r.get("geojson"),
            created_by=user.id,
        )
        route_repo.add(route)
        payload = route.to_dict()
        payload["risk_level"] = r.get("risk_level")
        payload["alternatives"] = result.get("alternatives", [])
        return jsonify(message="Transport route saved.", route=payload), 201
    except (GeocodeError, ValueError) as e:
        return jsonify(error=str(e)), 400


@bp.delete("/routes/<int:route_id>")
@require_permission("transport:manage_routes")
def remove_route(route_id):
    user, err = _portal_user()
    if err:
        return err
    route = route_repo.get(route_id)
    if route is None:
        return jsonify(error="Route not found."), 404
    route_repo.delete(route)
    return jsonify(message="Route removed.")
