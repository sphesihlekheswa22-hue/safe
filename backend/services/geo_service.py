"""Geospatial helpers: distance, route sampling, and coordinate sync."""
from __future__ import annotations

import math
from typing import Iterable

from sqlalchemy import inspect, text

from extensions import db
from services import gazetteer


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2 in degrees (0 = north)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def destination_point(lat: float, lon: float, bearing: float, distance_km: float) -> tuple[float, float]:
    """Return (lon, lat) reached by moving distance_km along bearing from the start point."""
    r = 6371.0
    br = math.radians(bearing)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_km / r)
        + math.cos(lat1) * math.sin(distance_km / r) * math.cos(br)
    )
    lon2 = lon1 + math.atan2(
        math.sin(br) * math.sin(distance_km / r) * math.cos(lat1),
        math.cos(distance_km / r) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lon2), math.degrees(lat2)


def sample_line(coords: list, max_points: int = 40) -> list[tuple[float, float]]:
    """Sample (lon, lat) pairs evenly along a LineString."""
    if not coords:
        return []
    if len(coords) <= max_points:
        return [(c[0], c[1]) for c in coords]
    step = max(1, len(coords) // max_points)
    sampled = [coords[i] for i in range(0, len(coords), step)]
    if sampled[-1] != coords[-1]:
        sampled.append(coords[-1])
    return [(c[0], c[1]) for c in sampled]


def sync_area_coords(area) -> None:
    """Fill latitude/longitude/radius_km on a RiskArea from the gazetteer."""
    lon, lat = gazetteer.coord_for(area.area_name)
    area.latitude = lat
    area.longitude = lon
    area.radius_km = gazetteer.radius_for(area.area_name)


def sync_event_coords(event) -> None:
    """Fill latitude/longitude on an Event from geocoding or the gazetteer."""
    from services.geocoding_service import GeocodeError, forward as geocode_forward

    try:
        result = geocode_forward(event.location)
        event.latitude = result["lat"]
        event.longitude = result["lng"]
        return
    except GeocodeError:
        pass
    lon, lat = gazetteer.coord_for(event.location)
    event.latitude = lat
    event.longitude = lon


def ensure_geo_columns() -> None:
    """Add geo columns to existing SQLite/Postgres tables if missing."""
    inspector = inspect(db.engine)
    alters: list[str] = []

    if "risk_areas" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("risk_areas")}
        if "latitude" not in cols:
            alters.append("ALTER TABLE risk_areas ADD COLUMN latitude FLOAT")
        if "longitude" not in cols:
            alters.append("ALTER TABLE risk_areas ADD COLUMN longitude FLOAT")
        if "radius_km" not in cols:
            alters.append("ALTER TABLE risk_areas ADD COLUMN radius_km FLOAT DEFAULT 2.5")

    if "events" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("events")}
        if "latitude" not in cols:
            alters.append("ALTER TABLE events ADD COLUMN latitude FLOAT")
        if "longitude" not in cols:
            alters.append("ALTER TABLE events ADD COLUMN longitude FLOAT")

    if "routes" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("routes")}
        for col in ("start_lat", "start_lng", "end_lat", "end_lng"):
            if col not in cols:
                alters.append(f"ALTER TABLE routes ADD COLUMN {col} FLOAT")

    if not alters:
        return

    with db.engine.begin() as conn:
        for stmt in alters:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
