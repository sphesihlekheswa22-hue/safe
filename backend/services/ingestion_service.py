"""Event ingestion service.

Centralizes creation of events from any source (manual form, simulated feed,
or external API). Keeping this in one place means the risk areas are always
recomputed consistently after new signals arrive.
"""
from extensions import db
from logger import get_logger
from models.event import Event
from services import risk_engine
from services.geo_service import sync_event_coords


log = get_logger(__name__)


def ingest_event(*, title, location, severity, description=None,
                 source="manual", created_by=None, recompute=True) -> Event:
    """Persist a new event and (optionally) refresh risk for that location only."""
    severity = int(severity)
    severity = max(1, min(5, severity))

    event = Event(
        title=title,
        description=description,
        location=location,
        severity=severity,
        source=source,
        created_by=created_by,
    )
    sync_event_coords(event)
    db.session.add(event)
    db.session.commit()

    if recompute:
        try:
            risk_engine.recompute_area(location)
        except Exception:
            log.exception("Risk recompute failed after creating event in %r", location)
            db.session.rollback()

    return event


def simulate_feed(samples, source="simulated") -> list:
    """Bulk-ingest events. Optional latitude/longitude for precise map placement."""
    created = []
    for s in samples:
        ev = Event(
            title=s["title"],
            description=s.get("description"),
            location=s["location"],
            severity=max(1, min(5, int(s.get("severity", 1)))),
            source=source,
        )
        if s.get("latitude") is not None and s.get("longitude") is not None:
            ev.latitude = float(s["latitude"])
            ev.longitude = float(s["longitude"])
        else:
            sync_event_coords(ev)
        db.session.add(ev)
        created.append(ev)
    db.session.commit()
    try:
        for loc in {ev.location for ev in created if ev.location}:
            risk_engine.recompute_area(loc)
    except Exception:
        log.exception("Risk recompute failed after simulated feed ingest")
        db.session.rollback()
    return created


def ingest_event_with_coords(**kwargs) -> Event:
    """Create an event with explicit map coordinates."""
    lat = kwargs.pop("latitude", None)
    lng = kwargs.pop("longitude", None)
    event = ingest_event(**kwargs)
    if lat is not None and lng is not None:
        event.latitude = float(lat)
        event.longitude = float(lng)
        db.session.commit()
    return event
