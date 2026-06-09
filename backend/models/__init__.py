"""Model package.

Importing the package imports every model so that ``db.create_all`` and
Flask-Migrate can discover all tables in one place.
"""
from models.user import User
from models.institution import Institution
from models.event import Event
from models.route import Route
from models.alert import Alert
from models.risk import RiskArea
from models.audit_log import AuditLog
from models.subscription import Subscription
from models.setting import SystemSetting

__all__ = [
    "User",
    "Institution",
    "Event",
    "Route",
    "Alert",
    "RiskArea",
    "AuditLog",
    "Subscription",
    "SystemSetting",
]
