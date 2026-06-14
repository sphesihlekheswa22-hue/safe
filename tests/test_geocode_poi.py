"""Tests for POI-aware geocode search."""
from conftest import auth
from services import geocoding_service, poi_service


def test_poi_search_poli_returns_police():
    results = poi_service.search_pois("poli", limit=10)
    assert len(results) >= 1
    assert all(r["category"] == "police" for r in results)
    assert all(r["source"] == "poi" for r in results)


def test_poi_search_nearest_hatfield_first():
    results = poi_service.search_pois(
        "poli",
        limit=5,
        near_lat=-25.7543,
        near_lng=28.2314,
    )
    assert len(results) >= 2
    assert results[0]["name"] == "Hatfield SAPS"
    assert results[0]["distance_km"] is not None
    assert results[0]["distance_km"] < results[1]["distance_km"]


def test_geocode_search_poli_merged():
    results = geocoding_service.search("poli", limit=8)
    assert len(results) >= 1
    assert results[0]["source"] == "poi"
    assert results[0]["category"] == "police"


def test_geocode_hatfield_still_returns_suburb():
    results = geocoding_service.search("hatfield", limit=8)
    assert len(results) >= 1
    names = [r["name"] for r in results]
    assert any("Hatfield" in n for n in names)


def test_geocode_api_poi_with_proximity(client, public_token):
    res = client.get(
        "/api/routes/geocode?q=poli&lat=-25.75&lng=28.19",
        headers=auth(public_token),
    )
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) >= 1
    poi = next(r for r in results if r.get("source") == "poi")
    assert poi["category"] == "police"
    assert "distance_km" in poi


def test_geocode_api_hospital_keyword(client, public_token):
    res = client.get(
        "/api/routes/geocode?q=hosp",
        headers=auth(public_token),
    )
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) >= 1
    assert any(r.get("category") == "hospital" for r in results)


def test_is_poi_keyword():
    assert poi_service.is_poi_keyword("poli")
    assert poi_service.is_poi_keyword("hosp")
    assert not poi_service.is_poi_keyword("hat")


def test_geocode_nearby_first_then_broad():
    """From Hatfield, nearby police appear before distant ones."""
    results = geocoding_service.search(
        "poli",
        limit=8,
        near_lat=-25.7543,
        near_lng=28.2314,
    )
    assert len(results) >= 2
    assert results[0]["name"] == "Hatfield SAPS"
    assert results[0]["distance_km"] <= 25
    assert all("distance_km" in r for r in results)


def test_geocode_jhb_user_gets_local_poli_first():
    """From Sandton, JHB police should rank above Pretoria police."""
    results = geocoding_service.search(
        "poli",
        limit=5,
        near_lat=-26.1076,
        near_lng=28.0587,
    )
    assert results[0]["name"] == "Sandton SAPS"


def test_geocode_hatfield_suburb_near_user_first():
    results = geocoding_service.search(
        "hat",
        limit=5,
        near_lat=-25.7543,
        near_lng=28.2314,
    )
    assert len(results) >= 1
    assert "Hatfield" in results[0]["name"]
    assert results[0]["distance_km"] is not None


def test_geocode_street_address_returns_nominatim():
    results = geocoding_service.search(
        "Visagie Street Pretoria",
        limit=5,
        near_lat=-25.7461,
        near_lng=28.1881,
    )
    assert len(results) >= 1
    assert results[0]["source"] == "nominatim"
    assert "Visagie" in results[0]["name"]
    assert "Gauteng" in results[0]["name"]


def test_geocode_numbered_address_keeps_house_number():
    results = geocoding_service.search(
        "123 Visagie Street Pretoria",
        limit=3,
        near_lat=-25.7461,
        near_lng=28.1881,
    )
    assert len(results) >= 1
    assert results[0]["name"].startswith("123")
    assert "Visagie" in results[0]["name"]


def test_geocode_suburb_without_poi_keyword():
    results = geocoding_service.search(
        "menlyn",
        limit=5,
        near_lat=-25.7842,
        near_lng=28.2756,
    )
    assert len(results) >= 1
    assert any(
        "Menlyn" in r["name"] or "menlyn" in r["name"].lower()
        for r in results
    )
