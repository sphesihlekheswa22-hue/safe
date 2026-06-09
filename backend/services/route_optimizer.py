"""Safe-route generation using OSRM road routing and live risk scoring."""
from __future__ import annotations

import logging

import requests

from models.alert import Alert
from models.event import Event
from models.risk import RiskArea
from services import gazetteer
from services.geo_service import haversine_km, sample_line

logger = logging.getLogger(__name__)

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
INCIDENT_RADIUS_KM = 0.6
W_INCIDENTS = 0.5
W_AREAS = 0.3
W_ALERTS = 0.2


def _risk_for_location(location: str) -> float:
    area = RiskArea.query.filter_by(area_name=location).first()
    return area.risk_score if area is not None else 25.0


def _risk_level(score: float) -> str:
    if score >= 70:
        return "DANGEROUS"
    if score >= 40:
        return "WARNING"
    return "SAFE"


def _score_route_path(coordinates: list, start_location: str, end_location: str) -> dict:
    """Score a route using incidents, area risk, and alerts along the corridor."""
    samples = sample_line(coordinates)
    events = Event.query.all()
    areas = RiskArea.query.all()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(20).all()

    incident_ids: set[int] = set()
    area_scores: list[float] = []
    alert_ids: set[int] = set()
    risk_zones_passed: list[str] = []

    for lon, lat in samples:
        for ev in events:
            if ev.latitude is None or ev.longitude is None:
                continue
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

    for alert in alerts:
        msg = (alert.message or "").lower()
        for zone in risk_zones_passed:
            if zone.lower() in msg:
                alert_ids.add(alert.id)
                break

    incident_hits = len(incident_ids)
    alert_hits = len(alert_ids)

    avg_area = sum(area_scores) / len(area_scores) if area_scores else (
        (_risk_for_location(start_location) + _risk_for_location(end_location)) / 2
    )
    incident_component = min(100.0, incident_hits * 12.0)
    alert_component = min(100.0, alert_hits * 25.0)

    risk_score = round(
        min(100.0, incident_component * W_INCIDENTS + avg_area * W_AREAS + alert_component * W_ALERTS),
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
    if alert_hits:
        reasons.append(f"{alert_hits} active alert(s) affect this corridor")

    if level == "SAFE":
        explanation = (
            f"Low-risk corridor from {start_location} to {end_location}. "
            + (reasons[0] if reasons else "No major incidents or high-risk zones detected.")
        )
    elif level == "WARNING":
        explanation = (
            f"Moderate risk route: {'; '.join(reasons) if reasons else 'some alerts nearby'}."
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


def _fetch_osrm_routes(start_coord: tuple, end_coord: tuple) -> list[dict]:
    """Return OSRM route geometries as GeoJSON features."""
    lon1, lat1 = start_coord
    lon2, lat2 = end_coord
    url = (
        f"{OSRM_BASE}/{lon1},{lat1};{lon2},{lat2}"
        "?overview=full&geometries=geojson&alternatives=true&steps=false"
    )
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        data = resp.json()
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
    except Exception as exc:
        logger.warning("OSRM routing failed: %s", exc)
        return []


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

    candidates = []
    osrm_routes = _fetch_osrm_routes(start_coord, end_coord)

    if osrm_routes:
        for i, item in enumerate(osrm_routes):
            coords = item["geojson"]["geometry"]["coordinates"]
            scoring = _score_route_path(coords, start_location, end_location)
            label = "Safest route" if i == 0 else f"Alternative route {i}"
            candidates.append({
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
                    },
                    "geometry": item["geojson"]["geometry"],
                },
                "risk_score": scoring["risk_score"],
                "risk_level": scoring["risk_level"],
                "explanation": scoring["explanation"],
                "distance_m": item.get("distance_m"),
                "duration_s": item.get("duration_s"),
            })
    else:
        fb = _fallback_route(start_coord, end_coord, start_location, end_location)
        candidates.append({
            "label": fb["label"],
            "geojson": fb["geojson"],
            "risk_score": fb["scoring"]["risk_score"],
            "risk_level": fb["scoring"]["risk_level"],
            "explanation": fb["scoring"]["explanation"],
        })

    # Sort by risk score ascending — safest first
    candidates.sort(key=lambda c: c["risk_score"])

    best = candidates[0]
    alternatives = candidates[1:]

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
        "geojson": best["geojson"],
        "alternatives": [
            {
                "label": alt["label"],
                "risk_score": alt["risk_score"],
                "risk_level": alt.get("risk_level"),
                "explanation": alt.get("explanation", ""),
                "geojson": alt["geojson"],
                "distance_m": alt.get("distance_m"),
                "duration_s": alt.get("duration_s"),
            }
            for alt in alternatives
        ],
    }
