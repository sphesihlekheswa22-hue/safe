"""Forward and reverse geocoding via OpenStreetMap Nominatim (South Africa)."""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

NOMINATIM = "https://nominatim.openstreetmap.org"
USER_AGENT = "SafeRouteAI/1.0 (South Africa safety routing)"
SA_BOUNDS = {"min_lat": -35.0, "max_lat": -22.0, "min_lon": 16.0, "max_lon": 33.0}
_last_request_at = 0.0


class GeocodeError(Exception):
    pass


def _throttle():
    """Nominatim allows max 1 request per second."""
    global _last_request_at
    elapsed = time.time() - _last_request_at
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    _last_request_at = time.time()


def _headers() -> dict:
    return {"User-Agent": USER_AGENT}


def _in_south_africa(lat: float, lon: float) -> bool:
    return (
        SA_BOUNDS["min_lat"] <= lat <= SA_BOUNDS["max_lat"]
        and SA_BOUNDS["min_lon"] <= lon <= SA_BOUNDS["max_lon"]
    )


def _short_name(item: dict) -> str:
    addr = item.get("address") or {}
    parts = [
        addr.get("amenity"),
        addr.get("road"),
        addr.get("suburb"),
        addr.get("town"),
        addr.get("city"),
        addr.get("municipality"),
        addr.get("state"),
    ]
    label = ", ".join(p for p in parts if p)
    return label or item.get("display_name", "Unknown location")


def search(query: str, limit: int = 6) -> list[dict]:
    """Return location suggestions for a free-text query within South Africa."""
    q = (query or "").strip()
    if len(q) < 2:
        return []

    _throttle()
    try:
        resp = requests.get(
            f"{NOMINATIM}/search",
            params={
                "q": q,
                "format": "json",
                "limit": limit,
                "countrycodes": "za",
                "addressdetails": 1,
            },
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json():
            lat = float(item["lat"])
            lon = float(item["lon"])
            if not _in_south_africa(lat, lon):
                continue
            results.append({
                "name": _short_name(item),
                "display_name": item.get("display_name", ""),
                "lat": lat,
                "lng": lon,
            })
        return results
    except Exception as exc:
        logger.warning("Geocode search failed: %s", exc)
        return []


def forward(query: str) -> dict:
    """Resolve a place name or address to coordinates."""
    matches = search(query, limit=1)
    if not matches:
        raise GeocodeError(f"Could not find '{query}' in South Africa. Try a more specific address.")
    m = matches[0]
    return {"name": m["name"], "display_name": m["display_name"], "lat": m["lat"], "lng": m["lng"]}


def reverse(lat: float, lng: float) -> dict:
    """Resolve coordinates to a human-readable place name."""
    if not _in_south_africa(lat, lng):
        raise GeocodeError("Location is outside South Africa.")

    _throttle()
    try:
        resp = requests.get(
            f"{NOMINATIM}/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        item = resp.json()
        return {
            "name": _short_name(item),
            "display_name": item.get("display_name", ""),
            "lat": lat,
            "lng": lng,
        }
    except GeocodeError:
        raise
    except Exception as exc:
        logger.warning("Reverse geocode failed: %s", exc)
        return {
            "name": f"{lat:.5f}, {lng:.5f}",
            "display_name": f"{lat:.5f}, {lng:.5f}",
            "lat": lat,
            "lng": lng,
        }


def resolve_location(
    label: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
) -> dict:
    """Use coordinates when provided, otherwise geocode the label."""
    if lat is not None and lng is not None:
        try:
            lat_f, lng_f = float(lat), float(lng)
        except (TypeError, ValueError) as exc:
            raise GeocodeError("Invalid coordinates.") from exc
        if not _in_south_africa(lat_f, lng_f):
            raise GeocodeError("Coordinates must be within South Africa.")
        if label and label.strip():
            return {"name": label.strip(), "display_name": label.strip(), "lat": lat_f, "lng": lng_f}
        return reverse(lat_f, lng_f)

    if not label or not label.strip():
        raise GeocodeError("Location name or coordinates are required.")

    return forward(label.strip())
