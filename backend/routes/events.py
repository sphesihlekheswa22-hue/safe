"""Events CRUD API. Reads are open to all roles; writes require an operational
role (enforced via the permission matrix)."""
from flask import Blueprint, request, jsonify

from models.event import Event
from services import ingestion_service as ingestion, risk_engine
from services.geo_service import sync_event_coords
from schemas.event_schema import validate_create, validate_update
from utils.validators import ValidationError
from repositories import event_repo
from middleware.rbac_middleware import require_permission, current_user
from utils.helpers import paginate_args

bp = Blueprint("events", __name__)


@bp.get("")
@require_permission("event:read")
def list_events():
    limit, _ = paginate_args(request, default_limit=200, max_limit=200)
    location = request.args.get("location")
    events = event_repo.list_recent(limit=limit, location=location)
    return jsonify(events=[e.to_dict() for e in events])


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
        source=data["source"],
        created_by=user.id if user else None,
    )
    return jsonify(message="Event created.", event=event.to_dict()), 201


@bp.put("/<int:event_id>")
@require_permission("event:write")
def update_event(event_id):
    event = event_repo.get(event_id)
    if event is None:
        return jsonify(error="Event not found."), 404
    try:
        changes = validate_update(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(e.to_dict()), 400

    for key, value in changes.items():
        setattr(event, key, value)
    if "location" in changes:
        sync_event_coords(event)
    event_repo.save()
    risk_engine.recompute_all_areas()
    return jsonify(message="Event updated.", event=event.to_dict())


@bp.delete("/<int:event_id>")
@require_permission("event:write")
def delete_event(event_id):
    event = event_repo.get(event_id)
    if event is None:
        return jsonify(error="Event not found."), 404
    event_repo.delete(event)
    risk_engine.recompute_all_areas()
    return jsonify(message="Event deleted.")
