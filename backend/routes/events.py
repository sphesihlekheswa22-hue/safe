"""Events CRUD API. Reads are open to all roles; writes require an operational
role (enforced via the permission matrix)."""
from flask import Blueprint, request, jsonify

from models.event import Event
from services import ingestion_service as ingestion, risk_engine
from services.city_events_service import events_for_city, DEFAULT_RADIUS_KM
from services.geo_service import sync_event_coords
from schemas.event_schema import validate_create, validate_update
from utils.validators import ValidationError
from repositories import event_repo
from middleware.rbac_middleware import require_permission, current_user
from utils.helpers import paginate_args
from utils.rbac import Role

bp = Blueprint("events", __name__)


def _can_modify_event(user, event) -> bool:
    """Admins may change any event; public users only their own submissions."""
    if user is None:
        return False
    if user.role == Role.SYSTEM_ADMIN:
        return True
    return event.created_by is not None and event.created_by == user.id


@bp.get("")
@require_permission("event:read")
def list_events():
    limit, _ = paginate_args(request, default_limit=200, max_limit=200)
    location = request.args.get("location")
    events = event_repo.list_recent(limit=limit, location=location)
    return jsonify(events=[e.to_dict() for e in events])


@bp.get("/my-city")
@require_permission("event:read")
def my_city_events():
    """Events in or near the user's city (proximity + location name match)."""
    city = (request.args.get("city") or "").strip()
    lat_raw = request.args.get("lat")
    lng_raw = request.args.get("lng")

    lat = lng = None
    if lat_raw not in (None, "") and lng_raw not in (None, ""):
        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
        except (TypeError, ValueError):
            return jsonify(error="lat and lng must be valid numbers."), 400

    if not city and (lat is None or lng is None):
        return jsonify(error="Provide city or both lat and lng."), 400

    try:
        radius = float(request.args.get("radius_km", DEFAULT_RADIUS_KM))
        radius = max(1.0, min(100.0, radius))
    except (TypeError, ValueError):
        radius = DEFAULT_RADIUS_KM

    events = events_for_city(city=city or None, lat=lat, lng=lng, radius_km=radius)
    return jsonify(
        city=city or None,
        lat=lat,
        lng=lng,
        radius_km=radius,
        count=len(events),
        events=[e.to_dict() for e in events],
    )


@bp.get("/<int:event_id>")
@require_permission("event:read")
def get_event(event_id):
    event = event_repo.get(event_id)
    if event is None:
        return jsonify(error="Event not found."), 404
    return jsonify(event=event.to_dict())


@bp.post("")
@require_permission("event:write")
def create_event():
    try:
        data = validate_create(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    user = current_user()
    event = ingestion.ingest_event(
        title=data["title"],
        location=data["location"],
        severity=data["severity"],
        description=data["description"],
        source="community" if user.role == Role.PUBLIC_USER else data.get("source", "manual"),
        created_by=user.id if user else None,
    )
    return jsonify(message="Event created.", event=event.to_dict()), 201


@bp.put("/<int:event_id>")
@require_permission("event:write")
def update_event(event_id):
    event = event_repo.get(event_id)
    if event is None:
        return jsonify(error="Event not found."), 404

    user = current_user()
    if not _can_modify_event(user, event):
        return jsonify(error="You can only edit events you created."), 403

    try:
        changes = validate_update(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    old_location = event.location
    for key, value in changes.items():
        setattr(event, key, value)
    if "location" in changes:
        sync_event_coords(event)
    event_repo.save()
    try:
        risk_engine.recompute_area(event.location)
        if "location" in changes and old_location and old_location != event.location:
            risk_engine.recompute_area(old_location)
    except Exception:
        pass
    return jsonify(message="Event updated.", event=event.to_dict())


@bp.delete("/<int:event_id>")
@require_permission("event:write")
def delete_event(event_id):
    event = event_repo.get(event_id)
    if event is None:
        return jsonify(message="Event already removed."), 200

    user = current_user()
    if not _can_modify_event(user, event):
        return jsonify(error="You can only delete events you created."), 403

    location = event.location
    event_repo.delete(event)
    try:
        risk_engine.recompute_area(location)
    except Exception:
        pass
    return jsonify(message="Event deleted.")
