"""Create all tables and seed demo data (idempotent).

Run from the project root:
    python scripts/setup_db.py
"""
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
from cli.seed import run_seed  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tables created.")
        run_seed()


if __name__ == "__main__":
    main()
