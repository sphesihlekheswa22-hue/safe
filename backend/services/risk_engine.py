"""Core risk scoring engine.

Implements the MVP risk formula:

    risk_score = (event_severity * 0.5)
               + (event_density   * 0.3)
               + (sentiment_score * 0.2)

Each input component is normalized to a 0..100 scale before weighting so the
final ``risk_score`` is always in the 0..100 range and directly comparable
across areas.
"""
from collections import defaultdict

from extensions import db
from models.event import Event
from models.risk import RiskArea
from services import sentiment_service as sentiment
from services import settings_service
from services.geo_service import sync_area_coords

# Default weights from the product spec. The System Admin can override these at
# runtime via the settings panel (see services.settings_service.risk_weights).
W_SEVERITY = 0.5
W_DENSITY = 0.3
W_SENTIMENT = 0.2

# Density saturates at this many events for a single area.
DENSITY_CAP = 10
# Severity is recorded on a 1..5 scale.
MAX_SEVERITY = 5


def _severity_component(events) -> float:
    if not events:
        return 0.0
    avg = sum(e.severity for e in events) / len(events)
    return (avg / MAX_SEVERITY) * 100.0


def _density_component(events) -> float:
    count = len(events)
    return (min(count, DENSITY_CAP) / DENSITY_CAP) * 100.0


def _sentiment_component(sentiment_score: float) -> float:
    """Map sentiment [-1,1] to a risk contribution [0,100].

    Very negative sentiment (-1) -> 100 risk. Very positive (+1) -> 0 risk.
    """
    return ((1.0 - sentiment_score) / 2.0) * 100.0


def compute_risk(events, sentiment_score: float, weights=None) -> float:
    """Return the weighted 0..100 risk score for a collection of events.

    ``weights`` is an optional (severity, density, sentiment) tuple; when not
    provided it is read from the admin-configured settings.
    """
    if weights is None:
        weights = settings_service.risk_weights()
    w_sev, w_den, w_sen = weights

    severity = _severity_component(events)
    density = _density_component(events)
    sentiment_risk = _sentiment_component(sentiment_score)

    score = (
        severity * w_sev
        + density * w_den
        + sentiment_risk * w_sen
    )
    return round(max(0.0, min(100.0, score)), 2)


def score_area(area_name: str) -> dict:
    """Compute the live risk score for a single named area from its events."""
    events = Event.query.filter_by(location=area_name).all()
    sentiment_score = sentiment.analyze_many(
        [f"{e.title} {e.description or ''}" for e in events]
    )
    risk = compute_risk(events, sentiment_score)
    return {
        "area_name": area_name,
        "risk_score": risk,
        "sentiment_score": round(sentiment_score, 3),
        "event_count": len(events),
        "components": {
            "severity": round(_severity_component(events), 2),
            "density": round(_density_component(events), 2),
            "sentiment_risk": round(_sentiment_component(sentiment_score), 2),
        },
    }


def recompute_all_areas() -> list:
    """Recompute and persist RiskArea rows for every location that has events.

    Returns the list of serialized RiskArea dicts.
    """
    # Respect the admin "risk engine enabled" toggle.
    if not settings_service.get("risk_engine_enabled", True):
        return []

    weights = settings_service.risk_weights()
    events = Event.query.all()
    grouped = defaultdict(list)
    for e in events:
        grouped[e.location].append(e)

    results = []
    for area_name, area_events in grouped.items():
        sentiment_score = sentiment.analyze_many(
            [f"{e.title} {e.description or ''}" for e in area_events]
        )
        risk = compute_risk(area_events, sentiment_score, weights=weights)

        area = RiskArea.query.filter_by(area_name=area_name).first()
        if area is None:
            area = RiskArea(area_name=area_name)
            db.session.add(area)
        area.risk_score = risk
        area.sentiment_score = round(sentiment_score, 3)
        sync_area_coords(area)
        results.append(area)

    db.session.commit()
    return [a.to_dict() for a in results]
