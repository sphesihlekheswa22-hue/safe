"""One-off migration: switch database to Gauteng (Pretoria) data only.

Run from project root:
    python scripts/migrate_gauteng.py
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
from cli.seed import migrate_gauteng_data  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        stats = migrate_gauteng_data()
        print("Gauteng migration complete:")
        for key, val in stats.items():
            print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
