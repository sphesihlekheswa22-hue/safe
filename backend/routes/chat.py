"""Safety Assistant chat API."""
from flask import Blueprint, request, jsonify

from middleware.rbac_middleware import require_permission, current_user
from middleware.rate_limit import rate_limit
from services import chat_service

bp = Blueprint("chat", __name__)


@bp.post("/message")
@rate_limit(max_requests=20, window_seconds=60)
@require_permission("chat:use")
def chat_message():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify(error="Message is required."), 400
    if len(message) > 2000:
        return jsonify(error="Message is too long (max 2000 characters)."), 400

    user = current_user()
    result = chat_service.answer(message, user)
    return jsonify(reply=result.get("reply", ""), suggestions=result.get("suggestions", []), action=result.get("action"))
