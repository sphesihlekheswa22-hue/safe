"""Core risk scoring engine.

Implements the MVP risk formula:

    risk_score = (event_severity * 0.5)
               + (event_density   * 0.3)
               + (sentiment_score * 0.2)
"""
from sqlalchemy import distinct

from extensions import db
from logger import get_logger
from models.event import Event
from models.risk import RiskArea
from services import sentiment_service as sentiment
from services import settings_service
from services.geo_service import sync_area_coords

log = get_logger(__name__)
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


def recompute_area(area_name: str, *, commit: bool = True) -> dict | None:
    """Recompute risk for one location only (fast path after create/delete)."""
    if not area_name or not settings_service.get("risk_engine_enabled", True):
        return None

    weights = settings_service.risk_weights()
    area_events = Event.query.filter_by(location=area_name).all()

    area = RiskArea.query.filter_by(area_name=area_name).first()
    if not area_events:
        if area is not None:
            db.session.delete(area)
            if commit:
                db.session.commit()
        return None

    sentiment_score = sentiment.analyze_many(
        [f"{e.title} {e.description or ''}" for e in area_events]
    )
    risk = compute_risk(area_events, sentiment_score, weights=weights)

    if area is None:
        area = RiskArea(area_name=area_name)
        db.session.add(area)
    area.risk_score = risk
    area.sentiment_score = round(sentiment_score, 3)
    sync_area_coords(area)
    if commit:
        db.session.commit()
    return area.to_dict()


def recompute_all_areas() -> list:
    """Recompute every area that has events (admin bulk action)."""
    if not settings_service.get("risk_engine_enabled", True):
        return []

    location_rows = db.session.query(distinct(Event.location)).all()
    results = []
    for (area_name,) in location_rows:
        if not area_name:
            continue
        try:
            row = recompute_area(area_name, commit=False)
            if row:
                results.append(row)
        except Exception:
            log.exception("Failed to recompute risk for %r", area_name)
            db.session.rollback()

    try:
        db.session.commit()
    except Exception:
        log.exception("Failed to commit bulk risk recompute")
        db.session.rollback()
        return []

    return results