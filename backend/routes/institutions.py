"""Institution management endpoints."""
from flask import Blueprint, request, jsonify

from extensions import db
from models.institution import Institution
from services import notification_service
from middleware.rbac_middleware import require_permission, current_user
from utils.security import clean_str
from utils.constants import INSTITUTION_TYPES

bp = Blueprint("institutions", __name__)


@bp.get("")
@require_permission("institution:read")
def list_institutions():
    institutions = Institution.query.order_by(Institution.name.asc()).all()
    return jsonify(institutions=[i.to_dict() for i in institutions])


@bp.get("/<int:inst_id>")
@require_permission("institution:read")
def get_institution(inst_id):
    inst = Institution.query.get(inst_id)
    if inst is None:
        return jsonify(error="Institution not found."), 404
    return jsonify(institution=inst.to_dict())


@bp.post("")
@require_permission("institution:write")
def create_institution():
    data = request.get_json(silent=True) or {}
    name = clean_str(data.get("name"), 200)
    if not name:
        return jsonify(error="Institution name is required."), 400
    if Institution.query.filter_by(name=name).first():
        return jsonify(error="An institution with that name already exists."), 409

    type_ = (clean_str(data.get("type"), 80) or "GENERIC").upper()
    if type_ not in INSTITUTION_TYPES:
        type_ = "GENERIC"

    inst = Institution(name=name, type=type_, location=clean_str(data.get("location"), 255))
    db.session.add(inst)
    db.session.commit()
    notification_service.record_audit(current_user(), "institution.created", target=name)
    return jsonify(message="Institution created.", institution=inst.to_dict()), 201


@bp.put("/<int:inst_id>")
@require_permission("institution:write")
def update_institution(inst_id):
    inst = Institution.query.get(inst_id)
    if inst is None:
        return jsonify(error="Institution not found."), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = clean_str(data.get("name"), 200)
        if not name:
            return jsonify(error="Institution name cannot be empty."), 400
        existing = Institution.query.filter_by(name=name).first()
        if existing and existing.id != inst.id:
            return jsonify(error="Another institution already uses that name."), 409
        inst.name = name
    if "type" in data:
        type_ = (clean_str(data.get("type"), 80) or "GENERIC").upper()
        inst.type = type_ if type_ in INSTITUTION_TYPES else "GENERIC"
    if "location" in data:
        inst.location = clean_str(data.get("location"), 255)

    db.session.commit()
    notification_service.record_audit(current_user(), "institution.updated", target=inst.name)
    return jsonify(message="Institution updated.", institution=inst.to_dict())


@bp.delete("/<int:inst_id>")
@require_permission("institution:write")
def delete_institution(inst_id):
    inst = Institution.query.get(inst_id)
    if inst is None:
        return jsonify(error="Institution not found."), 404
    for u in inst.users.all():
        u.institution_id = None
    name = inst.name
    db.session.delete(inst)
    db.session.commit()
    notification_service.record_audit(current_user(), "institution.deleted", target=name)
    return jsonify(message="Institution deleted.")
