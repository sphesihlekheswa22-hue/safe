"""Search curated Gauteng safety POIs for location autocomplete."""
from __future__ import annotations

import re
from typing import Optional

from data.sa_pois import SA_POIS, PoiEntry
from services.geo_service import haversine_km

CATEGORY_LABELS = {
    "police": "Police station",
    "hospital": "Hospital",
    "clinic": "Clinic",
    "station": "Station",
    "landmark": "Landmark",
}

# Short query prefixes → POI categories (longest match wins via sorted keys).
CATEGORY_ALIASES: dict[str, list[str]] = {
    "police": ["police"],
    "poli": ["police"],
    "pol": ["police"],
    "saps": ["police"],
    "cop": ["police"],
    "cops": ["police"],
    "hospital": ["hospital"],
    "hosp": ["hospital"],
    "clinic": ["clinic"],
    "clin": ["clinic"],
    "health": ["clinic", "hospital"],
    "station": ["station"],
    "stat": ["station"],
    "train": ["station"],
    "gautrain": ["station"],
    "airport": ["station"],
    "taxi": ["station"],
    "bus": ["station"],
    "landmark": ["landmark"],
    "monument": ["landmark"],
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _categories_for_query(q: str) -> set[str]:
    """Return POI categories implied by a short keyword query."""
    categories: set[str] = set()
    for prefix, cats in sorted(CATEGORY_ALIASES.items(), key=lambda x: -len(x[0])):
        if q == prefix or q.startswith(prefix) or prefix.startswith(q):
            categories.update(cats)
    return categories


def _match_score(q: str, poi: PoiEntry, implied_categories: set[str]) -> Optional[int]:
    """Lower score = better match. None = no match."""
    name = _normalize(poi["name"])
    aliases = [_normalize(a) for a in poi.get("aliases", [])]
    category = poi["category"]

    if q == name:
        return 0
    for alias in aliases:
        if q == alias:
            return 1
    if name.startswith(q):
        return 2
    for alias in aliases:
        if alias.startswith(q) or q.startswith(alias):
            return 3
    if implied_categories and category in implied_categories:
        return 4
    if q in name or any(q in alias for alias in aliases):
        return 5
    if category in implied_categories and len(q) >= 3:
        return 6
    return None


def _poi_result(poi: PoiEntry, distance_km: Optional[float] = None) -> dict:
    label = CATEGORY_LABELS.get(poi["category"], poi["category"].title())
    display = f"{label} · {poi['area']}"
    result = {
        "name": poi["name"],
        "display_name": display,
        "lat": poi["lat"],
        "lng": poi["lng"],
        "source": "poi",
        "category": poi["category"],
    }
    if distance_km is not None:
        result["distance_km"] = round(distance_km, 1)
    return result


def search_pois(
    query: str,
    limit: int = 8,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
) -> list[dict]:
    """Return POI suggestions matching query, optionally sorted nearest-first."""
    q = _normalize(query)
    if len(q) < 2:
        return []

    implied = _categories_for_query(q)
    scored: list[tuple[int, float, PoiEntry]] = []

    for poi in SA_POIS:
        score = _match_score(q, poi, implied)
        if score is None:
            continue
        dist = 0.0
        if near_lat is not None and near_lng is not None:
            dist = haversine_km(near_lat, near_lng, poi["lat"], poi["lng"])
        scored.append((score, dist, poi))

    scored.sort(key=lambda x: (x[0], x[1], x[2]["name"]))

    has_near = near_lat is not None and near_lng is not None
    if has_near:
        scored.sort(key=lambda x: (x[1], x[0], x[2]["name"]))
    results: list[dict] = []
    for score, dist, poi in scored[:limit]:
        results.append(_poi_result(poi, dist if has_near else None))
    return results


def is_poi_keyword(query: str) -> bool:
    """True when query looks like a POI category shortcut (e.g. poli, hosp)."""
    q = _normalize(query)
    return bool(_categories_for_query(q))


def categories_for_query(query: str) -> set[str]:
    """Return POI categories implied by a keyword query."""
    return _categories_for_query(_normalize(query))
