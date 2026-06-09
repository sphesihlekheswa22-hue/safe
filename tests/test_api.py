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


def test_analytics_requires_role(client, public_token, analyst_token):
    assert client.get("/api/reports/analytics", headers=auth(public_token)).status_code == 403
    assert client.get("/api/reports/analytics", headers=auth(analyst_token)).status_code == 200


def test_login_page_served(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"SafeRoute" in res.data


def test_alerts_scoped_by_role(client, public_token):
    res = client.get("/api/alerts", headers=auth(public_token))
    assert res.status_code == 200
    # Public user must not see analyst/admin-only alerts; only ALL or PUBLIC_USER.
    for a in res.get_json()["alerts"]:
        assert a["target_role"] in ("ALL", "PUBLIC_USER")
