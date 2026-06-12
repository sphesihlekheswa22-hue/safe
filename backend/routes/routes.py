"""Safe-route endpoints: list saved routes, generate new ones, delete, geocode."""
from flask import Blueprint, request, jsonify

from models.route import Route
from services import route_optimizer, geocoding_service
from services.geocoding_service import GeocodeError
from schemas.route_schema import validate_generate
from utils.validators import ValidationError
from repositories import route_repo
from middleware.rbac_middleware import require_permission, current_user

bp = Blueprint("routes", __name__)


@bp.get("/geocode")
@require_permission("route:read")
def geocode_search():
    """Autocomplete: search any South African address or place name."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify(results=[])
    try:
        limit = min(12, max(1, int(request.args.get("limit", 8))))
    except (TypeError, ValueError):
        limit = 8
    near_lat = request.args.get("lat", type=float)
    near_lng = request.args.get("lng", type=float)
    try:
        results = geocoding_service.search(
            q, limit=limit, near_lat=near_lat, near_lng=near_lng
        )
    except Exception:
        results = []
    return jsonify(results=results)


@bp.post("/geocode/reverse")
@require_permission("route:read")
def geocode_reverse():
    """Reverse-geocode GPS coordinates to a place name."""
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        return jsonify(error="lat and lng are required numbers."), 400
    try:
        result = geocoding_service.reverse(lat, lng)
        return jsonify(result=result)
    except GeocodeError as e:
        return jsonify(error=str(e)), 400


@bp.get("")
@require_permission("route:read")
def list_routes():
    routes = route_repo.list_recent()
    return jsonify(routes=[r.to_dict(include_geojson=False) for r in routes])


@bp.get("/<int:route_id>")
@require_permission("route:read")
def get_route(route_id):
    route = route_repo.get(route_id)
    if route is None:
        return jsonify(error="Route not found."), 404
    return jsonify(route=route.to_dict(include_geojson=True))


@bp.post("/generate")
@require_permission("route:generate")
def generate():
    try:
        data = validate_generate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    try:
        start = geocoding_service.resolve_location(
            data["start_location"], data["start_lat"], data["start_lng"]
        )
        end = geocoding_service.resolve_location(
            data["end_location"], data["end_lat"], data["end_lng"]
        )
    except GeocodeError as e:
        return jsonify(error=str(e)), 400

    try:
        result = route_optimizer.generate_route(
            start["name"],
            end["name"],
            start_coord=(start["lng"], start["lat"]),
            end_coord=(end["lng"], end["lat"]),
        )
    except Exception:
        return jsonify(error="Could not generate route. Try different locations or pick from suggestions."), 502

    user = current_user()
    route = Route(
        start_location=result["start_location"],
        end_location=result["end_location"],
        start_lat=result.get("start_lat"),
        start_lng=result.get("start_lng"),
        end_lat=result.get("end_lat"),
        end_lng=result.get("end_lng"),
        risk_score=result["risk_score"],
        geojson=result["geojson"],
        created_by=user.id if user else None,
    )
    route_repo.add(route)
    payload = route.to_dict()
    payload["alternatives"] = result.get("alternatives", [])
    payload["risk_level"] = result.get("risk_level")
    payload["explanation"] = result.get("explanation", "")
    return jsonify(message="Route generated.", route=payload), 201


@bp.delete("/<int:route_id>")
@require_permission("route:delete")
def delete_route(route_id):
    route = route_repo.get(route_id)
    if route is None:
        return jsonify(error="Route not found."), 404
    route_repo.delete(route)
    return jsonify(message="Route deleted.")
