"""Event ingestion service.

Centralizes creation of events from any source (manual form, simulated feed,
or external API). Keeping this in one place means the risk areas are always
recomputed consistently after new signals arrive.
"""
from extensions import db
from models.event import Event
from services import risk_engine
from services.geo_service import sync_event_coords


def ingest_event(*, title, location, severity, description=None,
                 source="manual", created_by=None, recompute=True) -> Event:
    """Persist a new event and (optionally) refresh risk areas."""
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
        risk_engine.recompute_all_areas()

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
    risk_engine.recompute_all_areas()
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
