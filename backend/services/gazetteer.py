"""Gauteng location gazetteer for coordinates and risk-zone radii."""
from __future__ import annotations

import hashlib
import re
from typing import Optional

# (longitude, latitude, radius_km) — Gauteng province (Pretoria / Tshwane focus)
GAZETTEER: dict[str, tuple[float, float, float]] = {
    # Pretoria / Tshwane
    "pretoria": (28.1881, -25.7461, 8.0),
    "pretoria cbd": (28.1881, -25.7461, 3.0),
    "pretoria station": (28.1897, -25.7589, 1.5),
    "pretoria east": (28.2789, -25.7625, 3.0),
    "pretoria north": (28.1789, -25.6789, 3.0),
    "hatfield": (28.2314, -25.7543, 2.0),
    "menlyn": (28.2756, -25.7842, 2.5),
    "brooklyn": (28.2345, -25.7712, 2.0),
    "soshanguve": (28.1114, -25.5129, 4.0),
    "mabopane": (28.0497, -25.4958, 3.0),
    "atteridgeville": (28.0628, -25.7736, 2.5),
    "mamelodi": (28.3912, -25.7089, 3.5),
    "centurion": (28.1878, -25.8603, 3.0),
    "rosslyn": (28.0891, -25.6012, 2.5),
    "tut": (28.1897, -25.5392, 3.0),
    "tut soshanguve": (28.1897, -25.5392, 2.5),
    "tut soshanguve campus": (28.1897, -25.5392, 2.0),
    "soshanguve campus": (28.1897, -25.5392, 2.0),
    "up hatfield": (28.2314, -25.7543, 2.0),
    "university of pretoria": (28.2314, -25.7543, 2.0),
    # Johannesburg metro (Gauteng)
    "johannesburg": (28.0473, -26.2041, 10.0),
    "johannesburg cbd": (28.0436, -26.2023, 3.0),
    "sandton": (28.0587, -26.1076, 3.0),
    "soweto": (27.8585, -26.2678, 5.0),
    "alexandra": (28.0897, -26.1019, 2.5),
    "or tambo airport": (28.2460, -26.1367, 4.0),
    "midrand": (28.1280, -25.9964, 3.0),
}

CITY_MARKERS = [
    {"name": "Pretoria", "lng": 28.1881, "lat": -25.7461},
    {"name": "Johannesburg", "lng": 28.0473, "lat": -26.2041},
    {"name": "Centurion", "lng": 28.1878, "lat": -25.8603},
]

# Major SA centres for nearest-place fallback when street-level reverse geocode fails.
SA_MAJOR_CITIES = [
    {"name": "Durban", "lat": -29.8587, "lng": 31.0218},
    {"name": "Pietermaritzburg", "lat": -29.6006, "lng": 30.3794},
    {"name": "Newcastle", "lat": -27.7574, "lng": 29.9321},
    {"name": "Richards Bay", "lat": -28.7807, "lng": 32.0383},
    {"name": "Cape Town", "lat": -33.9249, "lng": 18.4241},
    {"name": "Stellenbosch", "lat": -33.9321, "lng": 18.8602},
    {"name": "Bloemfontein", "lat": -29.0852, "lng": 26.1596},
    {"name": "Polokwane", "lat": -23.9045, "lng": 29.4689},
    {"name": "Gqeberha", "lat": -33.9608, "lng": 25.6022},
    {"name": "East London", "lat": -33.0153, "lng": 27.9116},
    {"name": "Nelspruit", "lat": -25.4653, "lng": 30.9703},
    {"name": "Kimberley", "lat": -28.7282, "lng": 24.7499},
    {"name": "Rustenburg", "lat": -25.6672, "lng": 27.2423},
    {"name": "Vereeniging", "lat": -26.6731, "lng": 27.9265},
]

DEFAULT_RADIUS_KM = 2.5
DEFAULT_MAP_CENTER = {"lng": 28.1881, "lat": -25.7461, "zoom": 11}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _title_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split())


def lookup(name: str) -> Optional[tuple[float, float, float]]:
    """Return (lon, lat, radius_km) for a location name, or None."""
    key = _normalize(name)
    if key in GAZETTEER:
        return GAZETTEER[key]
    for gaz_key, coords in GAZETTEER.items():
        if gaz_key in key or key in gaz_key:
            return coords
    return None


def lookup_city_near(lat: float, lng: float) -> Optional[str]:
    """Return the nearest known city label for proximity-biased geocode queries."""
    from services.geo_service import haversine_km

    best_name: str | None = None
    best_dist = float("inf")
    for marker in CITY_MARKERS:
        dist = haversine_km(lat, lng, marker["lat"], marker["lng"])
        if dist < best_dist:
            best_dist = dist
            best_name = marker["name"]
    if best_dist <= 80.0:
        return best_name
    return None


def nearest_place_name(lat: float, lng: float, max_km: float = 150.0) -> Optional[str]:
    """Return the closest known town/suburb/city name for a coordinate pair."""
    from services.geo_service import haversine_km

    best_name: str | None = None
    best_dist = float("inf")

    for key, coords in GAZETTEER.items():
        dist = haversine_km(lat, lng, coords[1], coords[0])
        if dist < best_dist:
            best_dist = dist
            best_name = _title_key(key)

    for marker in CITY_MARKERS + SA_MAJOR_CITIES:
        dist = haversine_km(lat, lng, marker["lat"], marker["lng"])
        if dist < best_dist:
            best_dist = dist
            best_name = marker["name"]

    if best_name and best_dist <= max_km:
        return best_name
    return None


def coord_for(name: str) -> tuple[float, float]:
    """Return (lon, lat) for a location; unknown names get deterministic coords in Gauteng."""
    entry = lookup(name)
    if entry:
        return (entry[0], entry[1])
    key = _normalize(name)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    lon = 28.05 + (int(h[:8], 16) % 1000) / 1000.0 * 0.35
    lat = -25.85 + (int(h[8:16], 16) % 1000) / 1000.0 * 0.25
    return (round(lon, 6), round(lat, 6))


def radius_for(name: str) -> float:
    entry = lookup(name)
    return entry[2] if entry else DEFAULT_RADIUS_KM
