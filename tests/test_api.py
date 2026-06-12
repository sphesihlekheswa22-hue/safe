"""General API + health tests."""
from conftest import auth


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_ready(client):
    res = client.get("/api/health/ready")
    assert res.status_code == 200
    assert res.get_json()["database"] == "up"


def test_dashboard_summary(client, public_token):
    res = client.get("/api/dashboard/summary", headers=auth(public_token))
    assert res.status_code == 200
    data = res.get_json()
    assert "kpis" in data and "risk_areas" in data
    assert "high_severity_events" in data["kpis"]
    assert "recent_events" in data
    assert "active_alerts" not in data


def test_analytics_requires_role(client, public_token, admin_token):
    assert client.get("/api/reports/analytics", headers=auth(public_token)).status_code == 403
    assert client.get("/api/reports/analytics", headers=auth(admin_token)).status_code == 200


def test_login_page_served(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"SafeRoute" in res.data


def test_register_page_served(client):
    res = client.get("/register")
    assert res.status_code == 200
    assert b"SafeRoute" in res.data


def test_geocode_requires_query(client, public_token):
    res = client.get("/api/routes/geocode?q=D", headers=auth(public_token))
    assert res.status_code == 200
    assert res.get_json()["results"] == []


def test_geocode_durban(client, public_token):
    res = client.get("/api/routes/geocode?q=Pretoria", headers=auth(public_token))
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) >= 1
    assert any("Pretoria" in r["name"] for r in results)


def test_realtime_events_snapshot(client):
    res = client.get("/api/realtime/events")
    assert res.status_code == 200
    assert "events" in res.get_json()


def test_alerts_api_removed(client, public_token):
    res = client.get("/api/alerts", headers=auth(public_token))
    assert res.status_code == 404


def test_chat_requires_auth(client):
    res = client.post("/api/chat/message", json={"message": "Hello"})
    assert res.status_code == 401


def test_chat_message_without_ai_key(client, public_token):
    res = client.post(
        "/api/chat/message",
        json={"message": "What incidents are active?"},
        headers=auth(public_token),
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "reply" in data and len(data["reply"]) > 0


def test_chat_refuses_unrelated_person_query(client, public_token, monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key-should-not-be-called")

    def _boom(*_a, **_k):
        raise AssertionError("Serper must not run for off-topic person queries")

    import services.serper_service as ss

    monkeypatch.setattr(ss, "fetch_sa_context", _boom)

    res = client.post(
        "/api/chat/message",
        json={"message": "Nelson Mandela"},
        headers=auth(public_token),
    )
    assert res.status_code == 200
    reply = res.get_json()["reply"].lower()
    assert "saferoute" in reply or "south africa" in reply
    assert "can't look up people" in reply or "only help" in reply
