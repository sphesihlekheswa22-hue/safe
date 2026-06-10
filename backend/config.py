"""Application configuration.

All secrets and connection strings are read from environment variables so that
nothing sensitive is hard-coded into the codebase.
"""
import os
from datetime import timedelta


def _build_database_uri() -> str:
    """Return the SQLAlchemy database URI.

    PostgreSQL is the target database. If ``DATABASE_URL`` is not provided we
    fall back to a local SQLite file so the project remains runnable out of the
    box for evaluation.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        # Normalize Heroku/Render/Neon URLs for SQLAlchemy + psycopg2.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://") :]
        elif url.startswith("postgresql://") and "+psycopg2" not in url:
            url = "postgresql+psycopg2://" + url[len("postgresql://") :]
        return url

    base_dir = os.path.abspath(os.path.dirname(__file__))
    return "sqlite:///" + os.path.join(base_dir, "saferoute_dev.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "120"))
    )

    JSON_SORT_KEYS = False

    # Set RATELIMIT_ENABLED=false to disable the in-memory rate limiter
    # (used by the test suite).
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"

    # Safety Assistant — Serper real-time SA search (primary)
    SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
    # Optional LLM (OpenAI / OpenRouter) — separate from Serper
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    CHAT_AI_ENABLED = os.environ.get("CHAT_AI_ENABLED", "true").lower() == "true"
