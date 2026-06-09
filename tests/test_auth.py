"""Authentication tests."""
from conftest import auth


def test_register_creates_public_user(client):
    res = client.post("/api/auth/register", json={
        "name": "New Person", "email": "newperson@example.com", "password": "Secret123",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["user"]["role"] == "PUBLIC_USER"
    assert "access_token" in data


def test_register_ignores_client_supplied_role(client):
    res = client.post("/api/auth/register", json={
        "name": "Sneaky", "email": "sneaky@example.com", "password": "Secret123",
        "role": "SYSTEM_ADMIN",
    })
    assert res.status_code == 201
    # Role must be forced to PUBLIC_USER regardless of input.
    assert res.get_json()["user"]["role"] == "PUBLIC_USER"


def test_register_rejects_weak_password(client):
    res = client.post("/api/auth/register", json={
        "name": "Weak", "email": "weak@example.com", "password": "short",
    })
    assert res.status_code == 400


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@saferoute.ai", "password": "wrong-password",
    })
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client, admin_token):
    res = client.get("/api/auth/me", headers=auth(admin_token))
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "SYSTEM_ADMIN"
