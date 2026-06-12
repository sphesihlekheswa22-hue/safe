"""Safe-route generation using OSRM road routing and live risk scoring."""
from __future__ import annotations

import logging

import requests

from models.event import Event
from models.risk import RiskArea
from services import gazetteer
from services.geo_service import (
    bearing_deg,
    destination_point,
    haversine_km,
    sample_line,
)

logger = logging.getLogger(__name__)

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
INCIDENT_RADIUS_KM = 0.6
BYPASS_OFFSET_KM = 2.2
W_INCIDENTS = 0.6
W_AREAS = 0.4


def _risk_for_location(location: str) -> float:
    area = RiskArea.query.filter_by(area_name=location).first()
    return area.risk_score if area is not None else 25.0


def _risk_level(score: float) -> str:
    if score >= 70:
        return "DANGEROUS"
    if score >= 40:
        return "WARNING"
    return "SAFE"


def _load_routing_context() -> tuple[list, list]:
    events = Event.query.filter(
        Event.latitude.isnot(None), Event.longitude.isnot(None)
    ).all()
    areas = RiskArea.query.all()
    return events, areas


def _events_near_path(
    coordinates: list,
    events: list | None = None,
) -> list[Event]:
    """Events within INCIDENT_RADIUS_KM of the sampled path, highest severity first."""
    if events is None:
        events, _ = _load_routing_context()
    samples = sample_line(coordinates)
    hits: dict[int, Event] = {}
    for lon, lat in samples:
        for ev in events:
            if haversine_km(lat, lon, ev.latitude, ev.longitude) <= INCIDENT_RADIUS_KM:
                hits[ev.id] = ev
    return sorted(hits.values(), key=lambda e: (-e.severity, e.id))


def _score_route_path(
    coordinates: list,
    start_location: str,
    end_location: str,
    *,
    events: list | None = None,
    areas: list | None = None,
) -> dict:
    """Score a route using incidents and area risk along the corridor."""
    if events is None or areas is None:
        loaded_events, loaded_areas = _load_routing_context()
        events = loaded_events if events is None else events
        areas = loaded_areas if areas is None else areas

    samples = sample_line(coordinates)
    incident_ids: set[int] = set()
    area_scores: list[float] = []
    risk_zones_passed: list[str] = []

    for lon, lat in samples:
        for ev in events:
            if haversine_km(lat, lon, ev.latitude, ev.longitude) <= INCIDENT_RADIUS_KM:
                incident_ids.add(ev.id)

        for area in areas:
            if area.latitude is None or area.longitude is None:
                continue
            radius = area.radius_km or 2.5
            if haversine_km(lat, lon, area.latitude, area.longitude) <= radius:
                area_scores.append(area.risk_score)
                if area.area_name not in risk_zones_passed:
                    risk_zones_passed.append(area.area_name)

    incident_hits = len(incident_ids)

    avg_area = sum(area_scores) / len(area_scores) if area_scores else (
        (_risk_for_location(start_location) + _risk_for_location(end_location)) / 2
    )
    incident_component = min(100.0, incident_hits * 12.0)

    risk_score = round(
        min(100.0, incident_component * W_INCIDENTS + avg_area * W_AREAS),
        2,
    )
    level = _risk_level(risk_score)

    reasons = []
    if incident_hits:
        reasons.append(f"{incident_hits} incident(s) near the route")
    if risk_zones_passed:
        high = [z for z in risk_zones_passed if _risk_for_location(z) >= 40]
        if high:
            reasons.append(f"passes through {', '.join(high[:3])}")

    if level == "SAFE":
        explanation = (
            f"Low-risk corridor from {start_location} to {end_location}. "
            + (reasons[0] if reasons else "No major incidents or high-risk zones detected.")
        )
    elif level == "WARNING":
        explanation = (
            f"Moderate risk route: {'; '.join(reasons) if reasons else 'some incidents nearby'}."
        )
    else:
        explanation = (
            f"High-risk route — avoid if possible: {'; '.join(reasons) if reasons else 'elevated area scores'}."
        )

    return {
        "risk_score": risk_score,
        "risk_level": level,
        "explanation": explanation,
        "incidents_on_route": incident_hits,
        "zones_passed": risk_zones_passed,
    }


def _parse_osrm_routes(data: dict) -> list[dict]:
    if data.get("code") != "Ok":
        return []
    features = []
    for i, route in enumerate(data.get("routes", [])):
        geom = route.get("geometry")
        if not geom:
            continue
        features.append({
            "index": i,
            "distance_m": route.get("distance"),
            "duration_s": route.get("duration"),
            "geojson": {
                "type": "Feature",
                "geometry": geom,
                "properties": {},
            },
        })
    return features


def _fetch_osrm_path(*waypoints: tuple, alternatives: bool = False) -> list[dict]:
    """Return OSRM route geometries for an ordered list of (lon, lat) waypoints."""
    if len(waypoints) < 2:
        return []
    path = ";".join(f"{lon},{lat}" for lon, lat in waypoints)
    alt = "true" if alternatives else "false"
    url = (
        f"{OSRM_BASE}/{path}"
        f"?overview=full&geometries=geojson&alternatives={alt}&steps=false"
    )
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        return _parse_osrm_routes(resp.json())
    except Exception as exc:
        logger.warning("OSRM routing failed for %s: %s", path[:80], exc)
        return []


def _fetch_osrm_routes(start_coord: tuple, end_coord: tuple) -> list[dict]:
    return _fetch_osrm_path(start_coord, end_coord, alternatives=True)


def _bypass_via_points(
    incidents: list[Event],
    start_coord: tuple,
    end_coord: tuple,
) -> list[tuple[float, float]]:
    """Via-point candidates placed perpendicular to the corridor to skirt incidents."""
    lon1, lat1 = start_coord
    lon2, lat2 = end_coord
    corridor_bearing = bearing_deg(lat1, lon1, lat2, lon2)
    points: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()

    for ev in incidents[:3]:
        for distance in (BYPASS_OFFSET_KM, BYPASS_OFFSET_KM + 0.8):
            for offset in (90, -90, 120, -120):
                lon, lat = destination_point(
                    ev.latitude,
                    ev.longitude,
                    corridor_bearing + offset,
                    distance,
                )
                key = (round(lon, 3), round(lat, 3))
                if key not in seen:
                    seen.add(key)
                    points.append((lon, lat))

    mid_lon = (lon1 + lon2) / 2
    mid_lat = (lat1 + lat2) / 2
    for ev in incidents[:2]:
        away = bearing_deg(ev.latitude, ev.longitude, mid_lat, mid_lon) + 180
        lon, lat = destination_point(ev.latitude, ev.longitude, away, BYPASS_OFFSET_KM)
        key = (round(lon, 3), round(lat, 3))
        if key not in seen:
            seen.add(key)
            points.append((lon, lat))

    return points


def _geometry_key(geojson: dict) -> str:
    coords = geojson.get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        return ""
    mid = coords[len(coords) // 2]
    first, last = coords[0], coords[-1]
    return (
        f"{round(first[0], 4)}:{round(first[1], 4)}:"
        f"{round(mid[0], 4)}:{round(mid[1], 4)}:"
        f"{round(last[0], 4)}:{round(last[1], 4)}:{len(coords)}"
    )


def _build_candidate(
    item: dict,
    scoring: dict,
    label: str,
    start_location: str,
    end_location: str,
) -> dict:
    return {
        "label": label,
        "geojson": {
            "type": "Feature",
            "properties": {
                "start": start_location,
                "end": end_location,
                "risk_score": scoring["risk_score"],
                "risk_level": scoring["risk_level"],
                "label": label,
                "distance_m": item.get("distance_m"),
                "duration_s": item.get("duration_s"),
                "incidents_on_route": scoring["incidents_on_route"],
            },
            "geometry": item["geojson"]["geometry"],
        },
        "risk_score": scoring["risk_score"],
        "risk_level": scoring["risk_level"],
        "explanation": scoring["explanation"],
        "incidents_on_route": scoring["incidents_on_route"],
        "distance_m": item.get("distance_m"),
        "duration_s": item.get("duration_s"),
    }


def _fetch_avoidance_routes(
    start_coord: tuple,
    end_coord: tuple,
    incidents: list[Event],
    start_location: str,
    end_location: str,
    ctx: tuple[list, list],
) -> list[dict]:
    """Request detour routes via waypoints that skirt blocking incidents."""
    events, areas = ctx
    candidates: list[dict] = []
    via_points = _bypass_via_points(incidents, start_coord, end_coord)

    for via in via_points[:8]:
        for osrm_item in _fetch_osrm_path(start_coord, via, end_coord):
            coords = osrm_item["geojson"]["geometry"]["coordinates"]
            scoring = _score_route_path(
                coords, start_location, end_location,
                events=events, areas=areas,
            )
            if scoring["incidents_on_route"] >= len(incidents):
                continue
            label = (
                "Safer detour (clear of incidents)"
                if scoring["incidents_on_route"] == 0
                else "Detour avoiding incidents"
            )
            candidates.append(_build_candidate(
                osrm_item, scoring, label, start_location, end_location,
            ))

    if len(incidents) >= 2:
        vias = via_points[:2]
        for osrm_item in _fetch_osrm_path(start_coord, vias[0], vias[1], end_coord):
            coords = osrm_item["geojson"]["geometry"]["coordinates"]
            scoring = _score_route_path(
                coords, start_location, end_location,
                events=events, areas=areas,
            )
            if scoring["incidents_on_route"] == 0:
                candidates.append(_build_candidate(
                    osrm_item, scoring, "Multi-point detour (clear of incidents)",
                    start_location, end_location,
                ))

    return candidates


def _fallback_route(start_coord: tuple, end_coord: tuple, start_location: str, end_location: str) -> dict:
    """Straight-line fallback when OSRM is unavailable."""
    mid = (
        round((start_coord[0] + end_coord[0]) / 2, 6),
        round((start_coord[1] + end_coord[1]) / 2, 6),
    )
    coords = [list(start_coord), list(mid), list(end_coord)]
    scoring = _score_route_path(coords, start_location, end_location)
    return {
        "geojson": {
            "type": "Feature",
            "properties": {"label": "Direct corridor (offline routing)"},
            "geometry": {"type": "LineString", "coordinates": coords},
        },
        "scoring": scoring,
        "label": "Direct corridor",
    }


def _label_candidates(candidates: list[dict]) -> None:
    """Apply human-readable labels after sorting."""
    if not candidates:
        return
    for i, c in enumerate(candidates):
        inc = c.get("incidents_on_route", 0)
        if i == 0:
            if inc == 0:
                c["label"] = "Safest route (clear of incidents)"
            else:
                c["label"] = f"Best available route ({inc} incident(s) nearby)"
        elif inc == 0 and "detour" not in (c.get("label") or "").lower():
            c["label"] = f"Alternate route avoiding incidents"
        elif inc > 0 and not c.get("label"):
            c["label"] = f"Alternative route ({inc} incident(s) nearby)"
        c["geojson"]["properties"]["label"] = c["label"]
        if i == 0 and inc > 0 and any(
            alt.get("incidents_on_route", 99) == 0 for alt in candidates[1:]
        ):
            c["explanation"] = (
                f"{c['explanation']} "
                "A clearer alternate route is available — compare options below."
            )


def generate_route(
    start_location: str,
    end_location: str,
    start_coord: tuple | None = None,
    end_coord: tuple | None = None,
) -> dict:
    """Return safest OSRM route with alternatives and risk explanations."""
    if start_coord is None:
        start_coord = gazetteer.coord_for(start_location)
    if end_coord is None:
        end_coord = gazetteer.coord_for(end_location)

    ctx = _load_routing_context()
    events, areas = ctx
    candidates: list[dict] = []
    seen_keys: set[str] = set()

    def add_candidate(candidate: dict) -> None:
        key = _geometry_key(candidate["geojson"])
        if key and key in seen_keys:
            return
        if key:
            seen_keys.add(key)
        candidates.append(candidate)

    osrm_routes = _fetch_osrm_routes(start_coord, end_coord)

    if osrm_routes:
        for i, item in enumerate(osrm_routes):
            coords = item["geojson"]["geometry"]["coordinates"]
            scoring = _score_route_path(
                coords, start_location, end_location,
                events=events, areas=areas,
            )
            label = "Direct route" if i == 0 else f"OSRM alternative {i}"
            add_candidate(_build_candidate(
                item, scoring, label, start_location, end_location,
            ))
    else:
        fb = _fallback_route(start_coord, end_coord, start_location, end_location)
        add_candidate({
            "label": fb["label"],
            "geojson": fb["geojson"],
            "risk_score": fb["scoring"]["risk_score"],
            "risk_level": fb["scoring"]["risk_level"],
            "explanation": fb["scoring"]["explanation"],
            "incidents_on_route": fb["scoring"]["incidents_on_route"],
        })

    blocking: list[Event] = []
    if candidates:
        reference_coords = candidates[0]["geojson"]["geometry"]["coordinates"]
        blocking = _events_near_path(reference_coords, events)
    if not blocking:
        line_coords = [list(start_coord), list(end_coord)]
        blocking = _events_near_path(line_coords, events)

    if blocking:
        for detour in _fetch_avoidance_routes(
            start_coord, end_coord, blocking, start_location, end_location, ctx,
        ):
            add_candidate(detour)

    candidates.sort(key=lambda c: (
        c.get("incidents_on_route", 999),
        c["risk_score"],
        c.get("distance_m") or 0,
    ))
    _label_candidates(candidates)

    best = candidates[0]
    alternatives = candidates[1:6]

    return {
        "start_location": start_location,
        "end_location": end_location,
        "start_lat": start_coord[1],
        "start_lng": start_coord[0],
        "end_lat": end_coord[1],
        "end_lng": end_coord[0],
        "risk_score": best["risk_score"],
        "risk_level": best.get("risk_level", _risk_level(best["risk_score"])),
        "explanation": best.get("explanation", ""),
        "incidents_on_route": best.get("incidents_on_route", 0),
        "geojson": best["geojson"],
        "alternatives": [
            {
                "label": alt["label"],
                "risk_score": alt["risk_score"],
                "risk_level": alt.get("risk_level"),
                "explanation": alt.get("explanation", ""),
                "incidents_on_route": alt.get("incidents_on_route", 0),
                "geojson": alt["geojson"],
                "distance_m": alt.get("distance_m"),
                "duration_s": alt.get("duration_s"),
            }
            for alt in alternatives
        ],
    }
