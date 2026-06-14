"""Forward and reverse geocoding via OpenStreetMap Nominatim (South Africa)."""
from __future__ import annotations

import logging
import re
import time
from typing import Optional

import requests

from services import gazetteer
from services import poi_service
from services.geo_service import haversine_km

logger = logging.getLogger(__name__)

NOMINATIM = "https://nominatim.openstreetmap.org"
USER_AGENT = "SafeRouteAI/1.0 (South Africa safety routing)"
SA_BOUNDS = {"min_lat": -35.0, "max_lat": -22.0, "min_lon": 16.0, "max_lon": 33.0}
# Nominatim viewbox: left, top, right, bottom (lon/lat)
SA_VIEWBOX = "16.0,-22.0,33.0,-35.0"
_last_request_at = 0.0
_nominatim_paused_until = 0.0
_search_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SEC = 300
LOCAL_RADIUS_KM = 25.0


class GeocodeError(Exception):
    pass


def _throttle():
    """Nominatim allows max 1 request per second."""
    global _last_request_at
    elapsed = time.time() - _last_request_at
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_request_at = time.time()


def _nominatim_available() -> bool:
    return time.time() >= _nominatim_paused_until


def _pause_nominatim(seconds: float = 120.0) -> None:
    global _nominatim_paused_until
    _nominatim_paused_until = time.time() + seconds


def _headers() -> dict:
    return {"User-Agent": USER_AGENT, "Accept-Language": "en"}


def _normalize(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def _in_south_africa(lat: float, lon: float) -> bool:
    return (
        SA_BOUNDS["min_lat"] <= lat <= SA_BOUNDS["max_lat"]
        and SA_BOUNDS["min_lon"] <= lon <= SA_BOUNDS["max_lon"]
    )


def _title_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split())


_STREET_RE = re.compile(
    r"\b("
    r"street|st|road|rd|avenue|ave|drive|dr|crescent|cres|close|lane|ln|"
    r"boulevard|blvd|way|place|pl|circle|court|ct|highway|hwy|freeway"
    r")\b",
    re.I,
)
_HOUSE_RE = re.compile(r"^(\d+[a-zA-Z]?)\s+")
_DISPLAY_SKIP = (
    "ward ",
    "metropolitan municipality",
    "local municipality",
    "south africa",
)


def _looks_like_address(query: str) -> bool:
    """True when the user is likely typing a street address."""
    q = (query or "").strip()
    if not q:
        return False
    if re.search(r"\d", q):
        return True
    return bool(_STREET_RE.search(q))


def _trim_display_name(display: str) -> str:
    if not display:
        return "Unknown location"
    parts: list[str] = []
    for raw in display.split(","):
        part = raw.strip()
        if not part:
            continue
        low = part.lower()
        if any(skip in low for skip in _DISPLAY_SKIP):
            continue
        if parts and parts[-1].lower() == low:
            continue
        parts.append(part)
    return ", ".join(parts[:5]) if parts else display


def _short_name(item: dict, query: str | None = None) -> str:
    """Build a concise South African address label from Nominatim data."""
    addr = item.get("address") or {}
    house = addr.get("house_number")
    if not house and query:
        match = _HOUSE_RE.match(query.strip())
        if match:
            house = match.group(1)

    road = (
        addr.get("road")
        or addr.get("pedestrian")
        or addr.get("footway")
        or addr.get("residential")
    )
    suburb = (
        addr.get("suburb")
        or addr.get("neighbourhood")
        or addr.get("quarter")
        or addr.get("hamlet")
    )
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
    )
    province = addr.get("state")
    postcode = addr.get("postcode")

    parts: list[str] = []
    street_line = " ".join(p for p in (house, road) if p)
    if street_line:
        parts.append(street_line)
    if suburb and suburb != city:
        parts.append(str(suburb))
    if city:
        parts.append(str(city))
    if province:
        parts.append(str(province))
    if postcode:
        parts.append(str(postcode))

    if parts:
        return ", ".join(parts)
    return _trim_display_name(item.get("display_name", "Unknown location"))


def _extract_city(item: dict) -> str | None:
    """Best-effort city label from a Nominatim reverse-geocode payload."""
    addr = item.get("address") or {}
    for key in ("city", "town", "municipality", "county", "state"):
        val = addr.get(key)
        if val:
            return str(val)
    return None


def _reverse_payload(item: dict | None, lat: float, lng: float) -> dict:
    if item:
        return {
            "name": _short_name(item),
            "display_name": item.get("display_name", ""),
            "city": _extract_city(item),
            "lat": lat,
            "lng": lng,
        }
    label = f"{lat:.5f}, {lng:.5f}"
    return {
        "name": label,
        "display_name": label,
        "city": None,
        "lat": lat,
        "lng": lng,
    }


def _result_key(lat: float, lng: float) -> str:
    return f"{round(lat, 4)}:{round(lng, 4)}"


def _merge_results(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for group in groups:
        for item in group:
            key = _result_key(item["lat"], item["lng"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _proximity_ranked_merge(
    *groups: list[dict],
    near_lat: float | None = None,
    near_lng: float | None = None,
    limit: int = 8,
    local_radius_km: float = LOCAL_RADIUS_KM,
) -> list[dict]:
    """Prefer results near the user, then broaden to farther matches."""
    seen: set[str] = set()
    near_tier: list[tuple[float, dict]] = []
    far_tier: list[tuple[float, dict]] = []
    flat: list[dict] = []

    for group in groups:
        for item in group:
            key = _result_key(item["lat"], item["lng"])
            if key in seen:
                continue
            seen.add(key)
            if near_lat is not None and near_lng is not None:
                dist = haversine_km(near_lat, near_lng, item["lat"], item["lng"])
                annotated = dict(item)
                annotated["distance_km"] = round(dist, 1)
                bucket = near_tier if dist <= local_radius_km else far_tier
                bucket.append((dist, annotated))
            else:
                flat.append(item)

    if near_lat is None or near_lng is None:
        return flat[:limit]

    near_tier.sort(key=lambda x: x[0])
    far_tier.sort(key=lambda x: x[0])
    return [item for _, item in near_tier + far_tier][:limit]


def _gazetteer_suggestions(
    query: str,
    limit: int = 8,
    near_lat: float | None = None,
    near_lng: float | None = None,
) -> list[dict]:
    """Instant local matches for known SA places (works offline / when Nominatim is slow)."""
    q = _normalize(query)
    if len(q) < 2:
        return []

    scored: list[tuple[int, str, tuple[float, float, float]]] = []
    for key, coords in gazetteer.GAZETTEER.items():
        if q in key or key.startswith(q) or (len(q) >= 3 and q in key.replace(" ", "")):
            priority = 0 if key == q else (1 if key.startswith(q) else 2)
            scored.append((priority, key, coords))

    scored.sort(key=lambda x: (x[0], len(x[1])))
    if near_lat is not None and near_lng is not None:
        scored.sort(
            key=lambda x: (
                haversine_km(near_lat, near_lng, x[2][1], x[2][0]),
                x[0],
                len(x[1]),
            )
        )
    results: list[dict] = []
    for _, key, (lon, lat, _radius) in scored[:limit]:
        title = _title_key(key)
        results.append({
            "name": title,
            "display_name": f"{title}, South Africa",
            "lat": lat,
            "lng": lon,
            "source": "gazetteer",
        })
    return results


def _nominatim_search(
    query: str,
    limit: int = 8,
    near_lat: float | None = None,
    near_lng: float | None = None,
) -> list[dict]:
    _throttle()
    try:
        params: dict = {
            "q": query,
            "format": "json",
            "limit": limit,
            "countrycodes": "za",
            "addressdetails": 1,
            "viewbox": SA_VIEWBOX,
            "bounded": 1,
            "dedupe": 1,
        }
        if near_lat is not None and near_lng is not None:
            params["lat"] = near_lat
            params["lon"] = near_lng
        resp = requests.get(
            f"{NOMINATIM}/search",
            params=params,
            headers=_headers(),
            timeout=12,
        )
        resp.raise_for_status()
        results: list[dict] = []
        for item in resp.json():
            lat = float(item["lat"])
            lon = float(item["lon"])
            if not _in_south_africa(lat, lon):
                continue
            short = _short_name(item, query=query)
            display = _trim_display_name(item.get("display_name", "")) or short
            results.append({
                "name": short,
                "display_name": display,
                "lat": lat,
                "lng": lon,
                "source": "nominatim",
            })
        return results
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            _pause_nominatim(180.0)
            logger.warning("Nominatim rate-limited; using local gazetteer for 3 min")
        else:
            logger.warning("Nominatim search failed for %r: %s", query, exc)
        return []
    except Exception as exc:
        logger.warning("Nominatim search failed for %r: %s", query, exc)
        return []


def _cache_key(query: str, near_lat: float | None, near_lng: float | None) -> str:
    base = _normalize(query)
    if near_lat is not None and near_lng is not None:
        return f"{base}@{round(near_lat, 2)}:{round(near_lng, 2)}"
    return base


def _expanded_nominatim_query(
    query: str,
    near_lat: float | None = None,
    near_lng: float | None = None,
) -> str | None:
    """Build a richer Nominatim query for POI keyword searches."""
    q = _normalize(query)
    implied = poi_service.categories_for_query(q)
    region = "South Africa"
    if near_lat is not None and near_lng is not None:
        city = gazetteer.lookup_city_near(near_lat, near_lng)
        if city:
            region = f"{city}, South Africa"
    if "police" in implied:
        return f"police station, {region}"
    if "hospital" in implied:
        return f"hospital, {region}"
    if "clinic" in implied:
        return f"clinic, {region}"
    if "station" in implied:
        return f"train station, {region}"
    return None


def search(
    query: str,
    limit: int = 8,
    near_lat: float | None = None,
    near_lng: float | None = None,
) -> list[dict]:
    """Return location suggestions for a free-text query within South Africa."""
    q = (query or "").strip()
    if len(q) < 2:
        return []

    cache_key = _cache_key(q, near_lat, near_lng)
    cached = _search_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SEC:
        return cached[1][:limit]

    has_near = near_lat is not None and near_lng is not None
    fetch_limit = max(limit * 4, 24) if has_near else limit

    is_address = _looks_like_address(q)
    is_poi_kw = poi_service.is_poi_keyword(q)

    pois = poi_service.search_pois(
        q, limit=fetch_limit, near_lat=near_lat, near_lng=near_lng
    )
    local = _gazetteer_suggestions(
        q, limit=fetch_limit, near_lat=near_lat, near_lng=near_lng
    )
    remote: list[dict] = []
    combined_local = len(pois) + len(local)

    should_nominatim = _nominatim_available() and (
        is_address
        or (len(q) >= 3 and not is_poi_kw)
        or (len(q) >= 4 and combined_local < fetch_limit)
    )
    if should_nominatim:
        remote = _nominatim_search(
            q, limit=fetch_limit, near_lat=near_lat, near_lng=near_lng
        )
        if not remote and "south africa" not in _normalize(q):
            remote = _nominatim_search(
                f"{q}, South Africa",
                limit=fetch_limit,
                near_lat=near_lat,
                near_lng=near_lng,
            )
    if is_poi_kw and _nominatim_available():
        expanded = _expanded_nominatim_query(q, near_lat=near_lat, near_lng=near_lng)
        if expanded:
            remote = _merge_results(
                remote,
                _nominatim_search(
                    expanded,
                    limit=fetch_limit,
                    near_lat=near_lat,
                    near_lng=near_lng,
                ),
            )

    if is_address:
        merge_groups = (remote, pois, local)
    else:
        merge_groups = (pois, local, remote)

    merged = _proximity_ranked_merge(
        *merge_groups,
        near_lat=near_lat,
        near_lng=near_lng,
        limit=limit,
    )
    _search_cache[cache_key] = (time.time(), merged)
    return merged


def forward(query: str) -> dict:
    """Resolve a place name or address to coordinates."""
    q = (query or "").strip()
    if not q:
        raise GeocodeError("Location name is required.")

    matches = search(q, limit=5)
    if matches:
        m = matches[0]
        return {
            "name": m["name"],
            "display_name": m["display_name"],
            "lat": m["lat"],
            "lng": m["lng"],
        }

    entry = gazetteer.lookup(q)
    if entry:
        lon, lat, _ = entry
        name = q.strip()
        return {
            "name": name,
            "display_name": f"{name}, South Africa",
            "lat": lat,
            "lng": lon,
        }

    raise GeocodeError(f"Could not find '{q}' in South Africa. Pick an address from the suggestions while typing.")


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
            timeout=12,
        )
        resp.raise_for_status()
        item = resp.json()
        return _reverse_payload(item, lat, lng)
    except GeocodeError:
        raise
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            _pause_nominatim(180.0)
        logger.warning("Reverse geocode failed: %s", exc)
        return _reverse_payload(None, lat, lng)
    except Exception as exc:
        logger.warning("Reverse geocode failed: %s", exc)
        return _reverse_payload(None, lat, lng)


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
