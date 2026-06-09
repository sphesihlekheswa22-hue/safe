"""Realtime layer (STUB).

NOTE: Full WebSocket push (e.g. flask-socketio) is intentionally NOT enabled to
keep the project runnable with zero extra infrastructure. Instead we expose a
Server-Sent Events (SSE) endpoint that streams the latest alerts by polling the
database. The frontend (static/js/websocket.js) consumes this and degrades to
plain polling if SSE is unavailable.
"""
import json
import os
import time

from flask import Blueprint, Response, jsonify, stream_with_context

from extensions import db
from models.alert import Alert

bp = Blueprint("realtime", __name__)

# Gunicorn sync workers kill silent connections; keepalives + short sessions avoid
# WORKER TIMEOUT on Render. EventSource auto-reconnects when a session ends.
_SSE_TICKS = int(os.environ.get("REALTIME_SSE_TICKS", "12"))  # ~2 min per session
_SSE_INTERVAL_SEC = int(os.environ.get("REALTIME_SSE_INTERVAL_SEC", "10"))


def _latest_alerts_payload():
    try:
        alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
        return [a.to_dict() for a in alerts]
    except Exception:
        db.session.rollback()
        return []


@bp.get("/alerts")
def alerts_snapshot():
    """JSON snapshot for polling fallback when SSE is unavailable."""
    return jsonify(alerts=_latest_alerts_payload())


@bp.get("/stream")
def stream():
    """SSE stream that emits the latest alerts roughly every 10 seconds.

    Public + unauthenticated by design (broadcast feed only). Sensitive data is
    never sent here.
    """

    @stream_with_context
    def generate():
        for _ in range(_SSE_TICKS):
            try:
                data = json.dumps({"alerts": _latest_alerts_payload()})
                yield f"data: {data}\n\n"
            finally:
                # Release the DB connection between long-lived SSE ticks.
                db.session.remove()
            # Heartbeat every second so gunicorn does not treat the worker as hung.
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
