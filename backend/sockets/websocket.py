"""Realtime layer (STUB).

NOTE: Full WebSocket push (e.g. flask-socketio) is intentionally NOT enabled to
keep the project runnable with zero extra infrastructure. Instead we expose a
Server-Sent Events (SSE) endpoint that streams the latest alerts by polling the
database. The frontend (static/js/websocket.js) consumes this and degrades to
plain polling if SSE is unavailable.
"""
import json
import time

from flask import Blueprint, Response, stream_with_context

from models.alert import Alert

bp = Blueprint("realtime", __name__)


def _latest_alerts_payload():
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    return [a.to_dict() for a in alerts]


@bp.get("/stream")
def stream():
    """SSE stream that emits the latest alerts roughly every 10 seconds.

    Public + unauthenticated by design (broadcast feed only). Sensitive data is
    never sent here.
    """

    @stream_with_context
    def generate():
        # A bounded number of ticks keeps dev servers from hanging forever.
        for _ in range(360):  # ~1 hour at 10s intervals
            data = json.dumps({"alerts": _latest_alerts_payload()})
            yield f"data: {data}\n\n"
            time.sleep(10)

    return Response(generate(), mimetype="text/event-stream")


def register(app):
    app.register_blueprint(bp, url_prefix="/api/realtime")
