"""Pytest fixtures.

Runs the whole app against a throwaway SQLite database so tests are fast and
require no external services.
"""
import os
import sys
import tempfile

import pytest

# Configure environment BEFORE importing the app (Config reads env at import).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-long-enough-32b"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RATELIMIT_ENABLED"] = "false"

from app_factory import create_app  # noqa: E402
from extensions import db  # noqa: E402
from cli.seed import run_seed  # noqa: E402


@pytest.fixture(scope="session")
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
        run_seed()
        yield app
        db.session.remove()
        db.drop_all()
    os.close(_DB_FD)
    try:
        os.remove(_DB_PATH)
    except OSError:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json().get("access_token")


@pytest.fixture()
def admin_token(client):
    return _login(client, "admin@saferoute.ai", os.environ.get("SEED_ADMIN_PASSWORD", "Admin#12345"))


@pytest.fixture()
def public_token(client):
    return _login(client, "public@saferoute.ai", "Passw0rd!")


def auth(token):
    return {"Authorization": "Bearer " + token}
