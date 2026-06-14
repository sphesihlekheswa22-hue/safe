"""Admin user CRUD — verifies API changes persist in the database."""
from conftest import auth

from extensions import db
from models.user import User
from utils.security import verify_password


def _users(client, admin_token):
    return client.get("/api/admin/users", headers=auth(admin_token)).get_json()["users"]


def test_admin_create_user_persists(client, admin_token):
    email = "crud-create@saferoute.ai"
    res = client.post(
        "/api/admin/users",
        headers=auth(admin_token),
        json={
            "name": "CRUD Create",
            "email": email,
            "password": "Testpass1",
            "role": "PUBLIC_USER",
        },
    )
    assert res.status_code == 201
    user_id = res.get_json()["user"]["id"]

    row = db.session.get(User, user_id)
    assert row is not None
    assert row.email == email
    assert row.role == "PUBLIC_USER"
    assert row.is_active is True
    assert verify_password(row.password_hash, "Testpass1")

    listed = next(u for u in _users(client, admin_token) if u["id"] == user_id)
    assert listed["name"] == "CRUD Create"


def test_admin_update_role_persists(client, admin_token):
    email = "crud-role@saferoute.ai"
    created = client.post(
        "/api/admin/users",
        headers=auth(admin_token),
        json={
            "name": "CRUD Role",
            "email": email,
            "password": "Testpass1",
            "role": "PUBLIC_USER",
        },
    ).get_json()["user"]

    res = client.put(
        f"/api/admin/users/{created['id']}/role",
        headers=auth(admin_token),
        json={"role": "SYSTEM_ADMIN"},
    )
    assert res.status_code == 200

    row = db.session.get(User, created["id"])
    assert row.role == "SYSTEM_ADMIN"


def test_admin_block_user_persists(client, admin_token):
    email = "crud-block@saferoute.ai"
    created = client.post(
        "/api/admin/users",
        headers=auth(admin_token),
        json={
            "name": "CRUD Block",
            "email": email,
            "password": "Testpass1",
            "role": "PUBLIC_USER",
        },
    ).get_json()["user"]

    res = client.put(
        f"/api/admin/users/{created['id']}/status",
        headers=auth(admin_token),
        json={"is_active": False},
    )
    assert res.status_code == 200
    assert res.get_json()["user"]["is_active"] is False

    row = db.session.get(User, created["id"])
    assert row.is_active is False


def test_admin_reset_password_persists(client, admin_token):
    email = "crud-password@saferoute.ai"
    created = client.post(
        "/api/admin/users",
        headers=auth(admin_token),
        json={
            "name": "CRUD Password",
            "email": email,
            "password": "Testpass1",
            "role": "PUBLIC_USER",
        },
    ).get_json()["user"]

    res = client.put(
        f"/api/admin/users/{created['id']}/password",
        headers=auth(admin_token),
        json={"password": "Newpass9"},
    )
    assert res.status_code == 200

    row = db.session.get(User, created["id"])
    assert verify_password(row.password_hash, "Newpass9")
    assert not verify_password(row.password_hash, "Testpass1")


def test_admin_delete_user_persists(client, admin_token):
    email = "crud-delete@saferoute.ai"
    created = client.post(
        "/api/admin/users",
        headers=auth(admin_token),
        json={
            "name": "CRUD Delete",
            "email": email,
            "password": "Testpass1",
            "role": "PUBLIC_USER",
        },
    ).get_json()["user"]
    user_id = created["id"]

    res = client.delete(f"/api/admin/users/{user_id}", headers=auth(admin_token))
    assert res.status_code == 200
    assert db.session.get(User, user_id) is None
    assert all(u["id"] != user_id for u in _users(client, admin_token))
