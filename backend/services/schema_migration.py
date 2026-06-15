"""Rename legacy plural table names to singular (users -> user, etc.)."""
from __future__ import annotations

from sqlalchemy import inspect, text

from extensions import db

# Old plural name -> new singular name
PLURAL_TO_SINGULAR = {
    "users": "user",
    "events": "event",
    "routes": "route",
    "subscriptions": "subscription",
    "audit_logs": "audit_log",
    "risk_areas": "risk_area",
    "system_settings": "system_setting",
}


def quote_table(bind, name: str) -> str:
    return bind.dialect.identifier_preparer.quote(name)


def _quote_table(bind, name: str) -> str:
    return quote_table(bind, name)


def ensure_singular_table_names() -> list[str]:
    """Rename plural tables when present; no-op if already migrated."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    renamed: list[str] = []

    with db.engine.begin() as conn:
        for old_name, new_name in PLURAL_TO_SINGULAR.items():
            if old_name not in tables or new_name in tables:
                continue
            old_q = _quote_table(db.engine, old_name)
            new_q = _quote_table(db.engine, new_name)
            conn.execute(text(f"ALTER TABLE {old_q} RENAME TO {new_q}"))
            renamed.append(f"{old_name} -> {new_name}")
            tables.discard(old_name)
            tables.add(new_name)

    return renamed


def resolve_table_name(tables: set[str], singular: str, plural: str) -> str | None:
    """Return the actual table name (singular preferred, plural fallback)."""
    if singular in tables:
        return singular
    if plural in tables:
        return plural
    return None
