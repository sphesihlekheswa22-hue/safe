"""Reporting service: aggregates data for analytics dashboards and exports."""
from models.user import User
from models.event import Event
from models.risk import RiskArea
from utils.rbac import Role
from utils.constants import MIN_SEVERITY, MAX_SEVERITY


def system_overview() -> dict:
    return {
        "users": User.query.count(),
        "events": Event.query.count(),
        "high_severity_events": Event.query.filter(Event.severity >= 4).count(),
        "risk_areas": RiskArea.query.count(),
    }


def users_by_role() -> dict:
    return {role: User.query.filter_by(role=role).count() for role in Role.all()}


def events_by_severity() -> dict:
    return {
        str(sev): Event.query.filter_by(severity=sev).count()
        for sev in range(MIN_SEVERITY, MAX_SEVERITY + 1)
    }


def top_risk_areas(limit=10) -> list:
    areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).limit(limit).all()
    return [a.to_dict() for a in areas]


def build_analytics_report() -> dict:
    return {
        "totals": system_overview(),
        "users_by_role": users_by_role(),
        "events_by_severity": events_by_severity(),
        "top_risk_areas": top_risk_areas(),
    }
