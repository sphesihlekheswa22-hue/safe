"""My City events API tests."""
from conftest import auth


def test_my_city_by_coords_near_pretoria(client, public_token):
    res = client.get(
        "/api/events/my-city",
        query_string={"city": "Pretoria", "lat": -25.7461, "lng": 28.1881},
        headers=auth(public_token),
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] > 0
    assert data["city"] == "Pretoria"
    assert len(data["events"]) == data["count"]


def test_my_city_by_name_only(client, public_token):
    res = client.get(
        "/api/events/my-city",
        query_string={"city": "Pretoria"},
        headers=auth(public_token),
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] > 0
    assert all("pretoria" in e["location"].lower() for e in data["events"])


def test_my_city_far_coords_empty(client, public_token):
    res = client.get(
        "/api/events/my-city",
        query_string={"city": "Remote", "lat": -33.9249, "lng": 18.4241},
        headers=auth(public_token),
    )
    assert res.status_code == 200
    assert res.get_json()["count"] == 0


def test_my_city_requires_params(client, public_token):
    res = client.get("/api/events/my-city", headers=auth(public_token))
    assert res.status_code == 400
