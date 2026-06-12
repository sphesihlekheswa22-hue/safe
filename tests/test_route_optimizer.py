"""Unit tests for incident-aware route optimization helpers."""
import pytest

from models.event import Event
from services.geo_service import bearing_deg, destination_point, haversine_km
from services import route_optimizer


def test_bearing_and_destination_roundtrip():
    lon, lat = 28.0473, -26.2041
    br = bearing_deg(lat, lon, -25.7461, 28.1881)
    dest_lon, dest_lat = destination_point(lat, lon, br, 10.0)
    assert haversine_km(lat, lon, dest_lat, dest_lon) == pytest.approx(10.0, rel=0.02)


def test_events_near_path_detects_close_event(app):
    with app.app_context():
        ev = Event(
            id=99,
            title="Blockade",
            location="Midpoint",
            severity=4,
            latitude=-26.6,
            longitude=27.9,
        )
        coords = [[27.9, -26.6], [28.1, -26.4]]
        hits = route_optimizer._events_near_path(coords, events=[ev])
        assert len(hits) == 1
        assert hits[0].id == 99


def test_events_near_path_ignores_distant_event(app):
    with app.app_context():
        ev = Event(
            id=100,
            title="Far away",
            location="Elsewhere",
            severity=3,
            latitude=-25.0,
            longitude=25.0,
        )
        coords = [[27.9, -26.6], [28.1, -26.4]]
        hits = route_optimizer._events_near_path(coords, events=[ev])
        assert hits == []


def test_bypass_via_points_offset_from_incident(app):
    with app.app_context():
        ev = Event(
            id=1,
            title="Protest",
            location="CBD",
            severity=5,
            latitude=-25.7461,
            longitude=28.1881,
        )
        start = (31.0, -29.9)
        end = (31.05, -29.82)
        points = route_optimizer._bypass_via_points([ev], start, end)
        assert len(points) >= 2
        for lon, lat in points:
            dist = haversine_km(ev.latitude, ev.longitude, lat, lon)
            assert dist >= route_optimizer.BYPASS_OFFSET_KM * 0.85


def test_generate_route_prefers_zero_incident_candidate(app, monkeypatch):
    """When a detour clears incidents, it should rank above the direct path."""
    direct_coords = [[31.0, -29.9], [31.02, -29.88], [31.05, -29.85]]
    detour_coords = [[31.0, -29.9], [31.08, -29.92], [31.05, -29.85]]

    def fake_fetch(start, end, alternatives=True):
        return [{
            "distance_m": 5000,
            "duration_s": 600,
            "geojson": {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": direct_coords},
                "properties": {},
            },
        }]

    def fake_path(*waypoints, alternatives=False):
        if len(waypoints) == 3:
            return [{
                "distance_m": 7000,
                "duration_s": 900,
                "geojson": {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": detour_coords},
                    "properties": {},
                },
            }]
        return []

    blocking = Event(
        id=7, title="Incident", location="Mid", severity=4,
        latitude=-29.885, longitude=31.02,
    )

    def fake_near(coords, events=None):
        if coords == direct_coords:
            return [blocking]
        return []

    def fake_score(coords, start_location, end_location, **kwargs):
        base = {
            "zones_passed": [],
            "risk_level": "SAFE",
            "explanation": "ok",
        }
        if coords == direct_coords:
            return {**base, "risk_score": 75.0, "risk_level": "DANGEROUS", "incidents_on_route": 1, "explanation": "near incident"}
        if coords == detour_coords:
            return {**base, "risk_score": 18.0, "incidents_on_route": 0, "explanation": "clear detour"}
        return route_optimizer._score_route_path(coords, start_location, end_location, **kwargs)

    monkeypatch.setattr(route_optimizer, "_fetch_osrm_routes", fake_fetch)
    monkeypatch.setattr(route_optimizer, "_fetch_osrm_path", fake_path)
    monkeypatch.setattr(route_optimizer, "_events_near_path", fake_near)
    monkeypatch.setattr(route_optimizer, "_score_route_path", fake_score)
    monkeypatch.setattr(route_optimizer, "_load_routing_context", lambda: ([blocking], []))

    with app.app_context():
        result = route_optimizer.generate_route(
            "Start", "End",
            start_coord=(31.0, -29.9),
            end_coord=(31.05, -29.85),
        )

    assert result["incidents_on_route"] == 0
    assert len(result["alternatives"]) >= 1
    direct_alts = [a for a in result["alternatives"] if a.get("incidents_on_route", 0) > 0]
    assert direct_alts, "Direct path with incidents should remain as an alternative"
