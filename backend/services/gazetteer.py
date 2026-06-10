"""South Africa location gazetteer for coordinates and risk-zone radii."""
from __future__ import annotations

import hashlib
import re
from typing import Optional

# (longitude, latitude, radius_km)
GAZETTEER: dict[str, tuple[float, float, float]] = {
    # Durban metro
    "durban": (31.0218, -29.8587, 8.0),
    "durban cbd": (31.0218, -29.8587, 2.5),
    "durban station": (31.0215, -29.8579, 1.5),
    "warwick junction": (31.0025, -29.8489, 1.2),
    "umlazi": (30.9136, -29.9614, 4.0),
    "ukzn": (30.9808, -29.8659, 2.0),
    "ukzn westville": (30.9808, -29.8659, 2.0),
    "pinetown": (30.8683, -29.8284, 3.0),
    "umhlanga": (31.0753, -29.7267, 2.5),
    "chatsworth": (30.8974, -29.9187, 3.5),
    "phoenix": (30.9812, -29.7012, 3.0),
    "durban harbour": (31.0362, -29.8682, 2.0),
    # Pretoria / Tshwane
    "pretoria": (28.1881, -25.7461, 8.0),
    "pretoria cbd": (28.1881, -25.7461, 3.0),
    "soshanguve": (28.1114, -25.5129, 4.0),
    "tut": (28.1897, -25.5392, 3.0),
    "tut soshanguve": (28.1897, -25.5392, 2.5),
    "tut soshanguve campus": (28.1897, -25.5392, 2.0),
    "soshanguve campus": (28.1897, -25.5392, 2.0),
    "mabopane": (28.0497, -25.4958, 3.0),
    "atteridgeville": (28.0628, -25.7736, 2.5),
    "centurion": (28.1878, -25.8603, 3.0),
    # Johannesburg metro
    "johannesburg": (28.0473, -26.2041, 10.0),
    "johannesburg cbd": (28.0436, -26.2023, 3.0),
    "sandton": (28.0587, -26.1076, 3.0),
    "soweto": (27.8585, -26.2678, 5.0),
    "alexandra": (28.0897, -26.1019, 2.5),
    "or tambo airport": (28.2460, -26.1367, 4.0),
    # Cape Town metro
    "cape town": (18.4241, -33.9249, 8.0),
    "cape town cbd": (18.4241, -33.9249, 2.5),
    "khayelitsha": (18.6769, -34.0422, 4.0),
    "mitchells plain": (18.6200, -34.0400, 3.5),
    "bellville": (18.6292, -33.8949, 2.5),
}

# Major city markers for map overview
CITY_MARKERS = [
    {"name": "Durban", "lng": 31.0218, "lat": -29.8587},
    {"name": "Johannesburg", "lng": 28.0473, "lat": -26.2041},
    {"name": "Cape Town", "lng": 18.4241, "lat": -33.9249},
]

DEFAULT_RADIUS_KM = 2.5
# Center of Durban for default map view
DEFAULT_MAP_CENTER = {"lng": 31.0218, "lat": -29.8587, "zoom": 11}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def lookup(name: str) -> Optional[tuple[float, float, float]]:
    """Return (lon, lat, radius_km) for a location name, or None."""
    key = _normalize(name)
    if key in GAZETTEER:
        return GAZETTEER[key]
    for gaz_key, coords in GAZETTEER.items():
        if gaz_key in key or key in gaz_key:
            return coords
    return None


def coord_for(name: str) -> tuple[float, float]:
    """Return (lon, lat) for a location; unknown names get deterministic coords in SA."""
    entry = lookup(name)
    if entry:
        return (entry[0], entry[1])
    key = _normalize(name)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    # Spread unknown places around Durban metro
    lon = 30.85 + (int(h[:8], 16) % 1000) / 1000.0 * 0.35
    lat = -29.95 + (int(h[8:16], 16) % 1000) / 1000.0 * 0.25
    return (round(lon, 6), round(lat, 6))


def radius_for(name: str) -> float:
    entry = lookup(name)
    return entry[2] if entry else DEFAULT_RADIUS_KM
