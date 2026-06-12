"""Model package.

Importing the package imports every model so that ``db.create_all`` and
Flask-Migrate can discover all tables in one place.
"""
from models.user import User
from models.event import Event
from models.route import Route
from models.risk import RiskArea
from models.audit_log import AuditLog
from models.subscription import Subscription
from models.setting import SystemSetting

__all__ = [
    "User",
    "Event",
    "Route",
    "RiskArea",
    "AuditLog",
    "Subscription",
    "SystemSetting",
]
