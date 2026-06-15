"""Create all tables and seed demo data (idempotent).

Run from the project root:
    python scripts/setup_db.py

Equivalent to:
    python scripts/create_database.py --seed
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.dirname(__file__)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from create_database import create_database  # noqa: E402


def main():
    create_database(drop=False, seed=True)


if __name__ == "__main__":
    main()
