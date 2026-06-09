"""Small reusable helper functions."""
from datetime import datetime


def iso(dt) -> str | None:
    """Serialize a datetime to an ISO-8601 UTC string."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat() + "Z"
    return str(dt)


def paginate_args(request, default_limit=50, max_limit=200):
    """Extract (limit, offset) from query params with sane bounds."""
    try:
        limit = int(request.args.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset


def ok(payload=None, **extra):
    """Build a standard success payload dict."""
    data = {"ok": True}
    if payload is not None:
        data.update(payload)
    data.update(extra)
    return data
