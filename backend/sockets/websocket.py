"""Realtime layer — SSE stream of recent incidents (events)."""
import json
import os
import time

from flask import Blueprint, Response, jsonify, stream_with_context

from extensions import db
from models.event import Event

bp = Blueprint("realtime", __name__)

_SSE_TICKS = int(os.environ.get("REALTIME_SSE_TICKS", "6"))
_SSE_INTERVAL_SEC = int(os.environ.get("REALTIME_SSE_INTERVAL_SEC", "10"))


def _latest_events_payload():
    try:
        events = Event.query.order_by(Event.created_at.desc()).limit(8).all()
        return [e.to_dict() for e in events]
    except Exception:
        db.session.rollback()
        return []


@bp.get("/events")
def events_snapshot():
    return jsonify(events=_latest_events_payload())


@bp.get("/stream")
def stream():
    @stream_with_context
    def generate():
        for _ in range(_SSE_TICKS):
            try:
                data = json.dumps({"events": _latest_events_payload()})
                yield f"data: {data}\n\n"
            finally:
                db.session.remove()
            for _ in range(_SSE_INTERVAL_SEC):
                yield ": keepalive\n\n"
                time.sleep(1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def register(app):
    app.register_blueprint(bp, url_prefix="/api/realtime")
