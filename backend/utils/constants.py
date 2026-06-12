"""Shared constants used across the application."""
from utils.rbac import Role  # re-exported for convenience

# Event severity bounds (1 = minor, 5 = critical).
MIN_SEVERITY = 1
MAX_SEVERITY = 5

# Alert severities.
ALERT_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# Risk level thresholds (0..100 scale).
RISK_HIGH_THRESHOLD = 70
RISK_MEDIUM_THRESHOLD = 40

# Risk engine weights (must sum to 1.0).
WEIGHT_SEVERITY = 0.5
WEIGHT_DENSITY = 0.3
WEIGHT_SENTIMENT = 0.2

__all__ = [
    "Role",
    "MIN_SEVERITY",
    "MAX_SEVERITY",
    "ALERT_SEVERITIES",
    "RISK_HIGH_THRESHOLD",
    "RISK_MEDIUM_THRESHOLD",
    "WEIGHT_SEVERITY",
    "WEIGHT_DENSITY",
    "WEIGHT_SENTIMENT",
]
