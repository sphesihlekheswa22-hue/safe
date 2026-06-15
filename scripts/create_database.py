"""Create and migrate the SafeRoute AI database.

Run from the project root:

    python scripts/create_database.py              # create / migrate tables only
    python scripts/create_database.py --seed       # create tables + demo data
    python scripts/create_database.py --drop       # drop all tables, then recreate
    python scripts/create_database.py --drop --seed

Uses DATABASE_URL from the environment (or .env). Falls back to SQLite when unset.
"""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_ROOT, ".env"))

_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app_factory import create_app  # noqa: E402
from extensions import db  # noqa: E402
from services.schema_migration import ensure_singular_table_names  # noqa: E402


def create_database(*, drop: bool = False, seed: bool = False) -> None:
    app = create_app()
    with app.app_context():
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        print(f"Database: {_safe_uri(uri)}")

        if drop:
            print("Dropping all tables...")
            db.drop_all()
            print("All tables dropped.")

        renamed = ensure_singular_table_names()
        if renamed:
            print("Renamed legacy tables:", ", ".join(renamed))

        db.create_all()
        print("Tables created.")

        if seed:
            from cli.seed import run_seed

            run_seed(refresh_events=True)
            print("Seed data loaded.")


def _safe_uri(uri: str) -> str:
    """Hide password in connection string for console output."""
    if "@" not in uri or "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    if "@" in rest and ":" in rest.split("@", 1)[0]:
        creds, host = rest.split("@", 1)
        user = creds.split(":", 1)[0]
        return f"{scheme}://{user}:****@{host}"
    return uri


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the SafeRoute AI database.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing tables before creating (destructive).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load demo users, events, and routes after creating tables.",
    )
    args = parser.parse_args()
    create_database(drop=args.drop, seed=args.seed)


if __name__ == "__main__":
    main()
