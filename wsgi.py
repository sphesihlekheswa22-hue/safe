"""WSGI entry point for production servers (gunicorn / uwsgi).

Example:
    gunicorn --bind 0.0.0.0:5000 wsgi:app
"""
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))

_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app_factory import create_app  # noqa: E402

app = create_app()
