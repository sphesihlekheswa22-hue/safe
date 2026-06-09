"""RBAC enforcement tests."""
from conftest import auth


def test_public_cannot_list_users(client, public_token):
    res = client.get("/api/admin/users", headers=auth(public_token))
    assert res.status_code == 403


def test_admin_can_list_users(client, admin_token):
    res = client.get("/api/admin/users", headers=auth(admin_token))
    assert res.status_code == 200
    assert "users" in res.get_json()


def test_public_cannot_create_event(client, public_token):
    res = client.post("/api/events", headers=auth(public_token), json={
        "title": "x", "location": "Downtown", "severity": 2,
    })
    assert res.status_code == 403


def test_public_cannot_create_alert(client, public_token):
    res = client.post("/api/alerts", headers=auth(public_token), json={"message": "hi"})
    assert res.status_code == 403


def test_only_admin_assigns_roles(client, public_token, analyst_token):
    for token in (public_token, analyst_token):
        res = client.put("/api/admin/users/1/role", headers=auth(token), json={"role": "SYSTEM_ADMIN"})
        assert res.status_code == 403


def test_admin_assigns_role(client, admin_token):
    # Find the public user and promote to analyst, then revert.
    users = client.get("/api/admin/users", headers=auth(admin_token)).get_json()["users"]
    target = next(u for u in users if u["email"] == "public@saferoute.ai")
    res = client.put(f"/api/admin/users/{target['id']}/role",
                     headers=auth(admin_token), json={"role": "SYSTEM_ANALYST"})
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "SYSTEM_ANALYST"
    # revert
    client.put(f"/api/admin/users/{target['id']}/role",
               headers=auth(admin_token), json={"role": "PUBLIC_USER"})
