"""AI / risk-engine endpoints.

- GET  /api/ai/risk-areas        -> persisted risk areas (all authenticated)
- GET  /api/ai/score/<area>      -> live computed score for one area
- POST /api/ai/recompute         -> recompute & persist all areas (analyst/admin)
- POST /api/ai/score             -> ad-hoc score for arbitrary inputs (analyst/admin)
"""
from flask import Blueprint, request, jsonify

from models.event import Event
from models.risk import RiskArea
from services import risk_engine, sentiment_service as sentiment, gazetteer
from utils.rbac import Role, require_roles

bp = Blueprint("ai", __name__)


@bp.get("/risk-areas")
@require_roles(*Role.all())
def risk_areas():
    areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    return jsonify(risk_areas=[a.to_dict() for a in areas])


@bp.get("/map-data")
@require_roles(*Role.all())
def map_data():
    """Bundled geospatial data for the Leaflet safety map."""
    areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    events = Event.query.order_by(Event.created_at.desc()).limit(50).all()
    return jsonify(
        map_center=gazetteer.DEFAULT_MAP_CENTER,
        cities=gazetteer.CITY_MARKERS,
        risk_areas=[a.to_dict() for a in areas],
        incidents=[e.to_dict() for e in events],
    )


@bp.get("/score/<path:area_name>")
@require_roles(*Role.all())
def score(area_name):
    return jsonify(result=risk_engine.score_area(area_name))


@bp.post("/recompute")
@require_roles(Role.SYSTEM_ADMIN)
def recompute():
    results = risk_engine.recompute_all_areas()
    return jsonify(message="Risk areas recomputed.", risk_areas=results)


@bp.post("/score")
@require_roles(Role.SYSTEM_ADMIN)
def score_adhoc():
    """Score an ad-hoc scenario without persisting it.

    Body: { "severity": 1..5, "event_count": int, "text": "..." }
    """
    data = request.get_json(silent=True) or {}

    class _E:  # lightweight stand-in matching the attributes risk_engine reads
        def __init__(self, severity):
            self.severity = severity

    try:
        severity = max(1, min(5, int(data.get("severity", 1))))
        count = max(0, int(data.get("event_count", 1)))
    except (TypeError, ValueError):
        return jsonify(error="severity and event_count must be integers."), 400

    text = data.get("text") or ""
    sentiment_score = sentiment.analyze(text)
    events = [_E(severity) for _ in range(count)]
    risk = risk_engine.compute_risk(events, sentiment_score)

    return jsonify(
        result={
            "risk_score": risk,
            "sentiment_score": round(sentiment_score, 3),
            "inputs": {"severity": severity, "event_count": count},
        }
    )
