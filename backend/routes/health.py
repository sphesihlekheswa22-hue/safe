"""Health and readiness probes."""
from flask import Blueprint, jsonify
from sqlalchemy import text

from extensions import db

bp = Blueprint("health", __name__)


@bp.get("")
def health():
    return jsonify(status="ok", service="saferoute-ai")


@bp.get("/ready")
def ready():
    """Readiness probe: verifies the database connection works."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ready", database="up")
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify(status="not-ready", database="down", detail=str(exc)), 503
