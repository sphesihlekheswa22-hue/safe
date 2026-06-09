"""Project entry point.

Loads environment variables from the root .env file, puts the ``backend``
package directory on the import path, and exposes the Flask ``app`` object.

Run with either:
    python run.py
or:
    flask --app run run        (so `flask seed` / `flask init-db` work too)
"""
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env at the project root.
load_dotenv(os.path.join(_ROOT, ".env"))

# Make backend modules importable as top-level packages (config, models, ...).
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app_factory import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
