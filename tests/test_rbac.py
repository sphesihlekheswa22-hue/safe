"""RBAC enforcement tests."""
from conftest import auth


def test_public_cannot_list_users(client, public_token):
    res = client.get("/api/admin/users", headers=auth(public_token))
    assert res.status_code == 403


def test_admin_can_list_users(client, admin_token):
    res = client.get("/api/admin/users", headers=auth(admin_token))
    assert res.status_code == 200
    assert "users" in res.get_json()


def test_public_can_create_event(client, public_token):
    res = client.post("/api/events", headers=auth(public_token), json={
        "title": "Community report",
        "location": "Downtown",
        "severity": 2,
        "description": "Test incident",
    })
    assert res.status_code == 201
    body = res.get_json()
    assert body["event"]["source"] == "community"


def test_only_admin_assigns_roles(client, public_token):
    res = client.put("/api/admin/users/1/role", headers=auth(public_token), json={"role": "SYSTEM_ADMIN"})
    assert res.status_code == 403


def test_admin_assigns_role(client, admin_token):
    users = client.get("/api/admin/users", headers=auth(admin_token)).get_json()["users"]
    target = next(u for u in users if u["email"] == "public@saferoute.ai")
    res = client.put(f"/api/admin/users/{target['id']}/role",
                     headers=auth(admin_token), json={"role": "SYSTEM_ADMIN"})
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "SYSTEM_ADMIN"
    client.put(f"/api/admin/users/{target['id']}/role",
               headers=auth(admin_token), json={"role": "PUBLIC_USER"})
