"""Platform settings service.

Central source of truth for runtime-configurable platform behaviour. Any key
not yet persisted falls back to a sane default, so the system runs correctly
even before an admin touches the settings panel (and before the table exists).
"""
from extensions import db
from models.setting import SystemSetting
from logger import get_logger

log = get_logger(__name__)

# Canonical defaults. The admin UI edits these; code reads them via get/get_all.
DEFAULTS = {
    # AI model control
    "ai_model": "rule_based",          # rule_based | ml_advanced
    "risk_engine_enabled": True,
    "sentiment_mode": "lexicon",       # lexicon | advanced
    "weight_severity": 0.5,
    "weight_density": 0.3,
    "weight_sentiment": 0.2,
    # Security control
    "registration_open": True,
    "rate_limit_max": 10,
    "rate_limit_window": 60,
    "jwt_expiry_minutes": 120,
}

# Which keys the admin panel is allowed to write, with light coercion.
_COERCERS = {
    "ai_model": lambda v: str(v) if v in ("rule_based", "ml_advanced") else "rule_based",
    "risk_engine_enabled": lambda v: bool(v),
    "sentiment_mode": lambda v: str(v) if v in ("lexicon", "advanced") else "lexicon",
    "weight_severity": lambda v: max(0.0, min(1.0, float(v))),
    "weight_density": lambda v: max(0.0, min(1.0, float(v))),
    "weight_sentiment": lambda v: max(0.0, min(1.0, float(v))),
    "registration_open": lambda v: bool(v),
    "rate_limit_max": lambda v: max(1, min(1000, int(v))),
    "rate_limit_window": lambda v: max(1, min(3600, int(v))),
    "jwt_expiry_minutes": lambda v: max(5, min(10080, int(v))),
}


def _safe_rollback():
    """Roll back a poisoned transaction so later queries in the same request
    don't fail with ``InFailedSqlTransaction`` (e.g. before the table exists)."""
    try:
        db.session.rollback()
    except Exception:
        pass


def get(key, default=None):
    """Return a single setting value, falling back to DEFAULTS then ``default``."""
    fallback = DEFAULTS.get(key, default)
    try:
        row = SystemSetting.query.filter_by(key=key).first()
        if row is None:
            return fallback
        return row.get_value()
    except Exception as exc:  # table may not exist yet (pre-migration)
        log.debug("settings.get(%s) fell back to default: %s", key, exc)
        _safe_rollback()
        return fallback


def get_all():
    """Return every setting (defaults merged with any persisted overrides)."""
    merged = dict(DEFAULTS)
    try:
        for row in SystemSetting.query.all():
            merged[row.key] = row.get_value()
    except Exception as exc:
        log.debug("settings.get_all fell back to defaults: %s", exc)
        _safe_rollback()
    return merged


def set(key, value):
    """Persist a single setting, applying coercion if a coercer exists."""
    if key in _COERCERS:
        value = _COERCERS[key](value)
    row = SystemSetting.query.filter_by(key=key).first()
    if row is None:
        row = SystemSetting(key=key)
        db.session.add(row)
    row.set_value(value)
    db.session.commit()
    return value


def set_many(data: dict):
    """Persist multiple known settings; ignores unknown keys. Returns updated map."""
    updated = {}
    for key, value in (data or {}).items():
        if key not in _COERCERS:
            continue
        try:
            updated[key] = _COERCERS[key](value)
        except (TypeError, ValueError):
            continue
        row = SystemSetting.query.filter_by(key=key).first()
        if row is None:
            row = SystemSetting(key=key)
            db.session.add(row)
        row.set_value(updated[key])
    db.session.commit()
    return updated


def risk_weights():
    """Return normalized (severity, density, sentiment) weights."""
    s = get("weight_severity", 0.5)
    d = get("weight_density", 0.3)
    n = get("weight_sentiment", 0.2)
    total = s + d + n
    if total <= 0:
        return 0.5, 0.3, 0.2
    return s / total, d / total, n / total
