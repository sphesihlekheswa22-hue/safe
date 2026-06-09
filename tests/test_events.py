"""Event CRUD + risk engine tests."""
from conftest import auth


def test_analyst_can_create_event_and_recompute_risk(client, analyst_token):
    res = client.post("/api/events", headers=auth(analyst_token), json={
        "title": "Violent robbery downtown", "location": "TestArea",
        "severity": 5, "description": "danger violent attack unsafe",
    })
    assert res.status_code == 201
    event_id = res.get_json()["event"]["id"]

    # Risk area should now exist for TestArea with a high score.
    areas = client.get("/api/ai/risk-areas", headers=auth(analyst_token)).get_json()["risk_areas"]
    test_area = next((a for a in areas if a["area_name"] == "TestArea"), None)
    assert test_area is not None
    assert test_area["risk_score"] > 50

    # Cleanup.
    assert client.delete(f"/api/events/{event_id}", headers=auth(analyst_token)).status_code == 200


def test_event_validation(client, analyst_token):
    res = client.post("/api/events", headers=auth(analyst_token), json={"title": "no location"})
    assert res.status_code == 400


def test_severity_bounds(client, analyst_token):
    res = client.post("/api/events", headers=auth(analyst_token), json={
        "title": "bad", "location": "X", "severity": 9,
    })
    assert res.status_code == 400


def test_route_generation(client, public_token):
    res = client.post("/api/routes/generate", headers=auth(public_token), json={
        "start_location": "Downtown", "end_location": "Harbor",
    })
    assert res.status_code == 201
    route = res.get_json()["route"]
    assert "geojson" in route
    assert route["geojson"]["geometry"]["type"] == "LineString"
