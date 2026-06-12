"""Filter events by city name and/or proximity to user coordinates."""
from __future__ import annotations

from models.event import Event
from services.geo_service import haversine_km

DEFAULT_RADIUS_KM = 25.0


def events_for_city(
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = DEFAULT_RADIUS_KM,
    limit: int = 50,
) -> list[Event]:
    """Return events near the user or whose location mentions the city."""
    city_clean = (city or "").strip()
    city_lower = city_clean.lower()
    has_coords = lat is not None and lng is not None

    matched: list[Event] = []
    for event in Event.query.order_by(Event.created_at.desc()).all():
        ok = False
        if (
            has_coords
            and event.latitude is not None
            and event.longitude is not None
        ):
            dist = haversine_km(lat, lng, event.latitude, event.longitude)
            if dist <= radius_km:
                ok = True
        if not ok and city_lower and city_lower in (event.location or "").lower():
            ok = True
        if ok:
            matched.append(event)
        if len(matched) >= limit:
            break
    return matched
