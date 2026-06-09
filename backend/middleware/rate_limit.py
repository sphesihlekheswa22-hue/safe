"""A tiny in-memory rate limiter.

Dependency-free fixed-window limiter keyed by client IP + endpoint. Good enough
to protect sensitive endpoints (e.g. login) in the MVP. For multi-process /
multi-host deployments this would be backed by Redis instead.
"""
import time
from collections import defaultdict
from functools import wraps

from flask import request, jsonify, current_app

_BUCKETS = defaultdict(list)  # key -> list[timestamps]


def _dynamic_limits(default_max, default_window):
    """Read admin-configured limits from settings, falling back to defaults.

    Imported lazily to avoid a circular import at module load.
    """
    try:
        from services import settings_service

        return (
            int(settings_service.get("rate_limit_max", default_max)),
            int(settings_service.get("rate_limit_window", default_window)),
        )
    except Exception:
        return default_max, default_window


def rate_limit(max_requests=30, window_seconds=60, dynamic=True):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_app.config.get("RATELIMIT_ENABLED", True):
                return view_func(*args, **kwargs)

            # Admin can tune limits live from the security panel.
            if dynamic:
                max_req, window = _dynamic_limits(max_requests, window_seconds)
            else:
                max_req, window = max_requests, window_seconds

            now = time.time()
            key = f"{request.remote_addr}:{request.endpoint}"
            window_start = now - window

            timestamps = [t for t in _BUCKETS[key] if t >= window_start]
            if len(timestamps) >= max_req:
                retry = int(window - (now - timestamps[0]))
                resp = jsonify(error="Too many requests. Please slow down.",
                               retry_after=max(retry, 1))
                resp.status_code = 429
                return resp

            timestamps.append(now)
            _BUCKETS[key] = timestamps
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
