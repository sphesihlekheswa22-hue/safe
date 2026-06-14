"""Reverse geocode should return human place names, never raw coordinates."""
from services import geocoding_service, gazetteer


def test_reverse_fallback_never_returns_coordinates():
    lat, lng = -28.17062, 30.16767
    payload = geocoding_service._fallback_location_label(lat, lng, None)
    assert payload["name"]
    assert not geocoding_service._looks_like_coords(payload["name"])
    assert "Near" in payload["name"] or payload["name"] == "Your area"
    assert payload["approximate"] is True


def test_nearest_place_for_kzn_coordinates():
    name = gazetteer.nearest_place_name(-28.17062, 30.16767)
    assert name
    assert name in {"Newcastle", "Durban", "Pietermaritzburg", "Richards Bay"}


def test_reverse_payload_rejects_coordinate_name():
    item = {
        "display_name": "-28.17062, 30.16767",
        "address": {},
    }
    payload = geocoding_service._reverse_payload(item, -28.17062, 30.16767)
    assert not geocoding_service._looks_like_coords(payload["name"])


def test_reverse_api_returns_label_not_coords(client, public_token):
    from conftest import auth

    res = client.post(
        "/api/routes/geocode/reverse",
        headers=auth(public_token),
        json={"lat": -28.17062, "lng": 30.16767},
    )
    assert res.status_code == 200
    result = res.get_json()["result"]
    assert result["name"]
    assert not geocoding_service._looks_like_coords(result["name"])
