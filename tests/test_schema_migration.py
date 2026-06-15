"""Tests for plural -> singular table rename migration."""
import os
import sys
import tempfile

import pytest
from sqlalchemy import inspect

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from extensions import db  # noqa: E402
from services.schema_migration import ensure_singular_table_names  # noqa: E402


def test_fresh_db_uses_singular_table_names(app):
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        assert "user" in tables
        assert "event" in tables
        assert "route" in tables
        assert "users" not in tables
        assert "events" not in tables


def test_rename_plural_tables_on_existing_db():
    """Rename migration on a legacy DB without touching the shared session database."""
    from flask import Flask

    fd, path = tempfile.mkstemp(suffix=".db")
    uri = "sqlite:///" + path.replace("\\", "/")
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    try:
        with app.app_context():
            with db.engine.begin() as conn:
                conn.exec_driver_sql(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(120), "
                    "email VARCHAR(255) UNIQUE, password_hash VARCHAR(255), "
                    "role VARCHAR(40), is_active BOOLEAN, created_at DATETIME)"
                )
            renamed = ensure_singular_table_names()
            tables = set(inspect(db.engine).get_table_names())
            assert "users -> user" in renamed
            assert "user" in tables
            assert "users" not in tables
    finally:
        os.close(fd)
        try:
            os.remove(path)
        except OSError:
            pass
