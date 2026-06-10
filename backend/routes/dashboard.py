"""Dashboard summary endpoint feeding the KPI cards and feeds.

Returns a single payload the frontend consumes to render the dashboard. The
content is lightly tailored to the caller's role.
"""
from flask import Blueprint, jsonify

from models.event import Event
from models.alert import Alert
from models.route import Route
from models.risk import RiskArea
from utils.rbac import Role, require_roles, current_user

bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
@require_roles(*Role.all())
def summary():
    user = current_user()

    total_events = Event.query.count()
    total_routes = Route.query.count()
    risk_areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()

    high_risk = [a for a in risk_areas if a.risk_level in ("HIGH", "CRITICAL")]
    avg_risk = (
        round(sum(a.risk_score for a in risk_areas) / len(risk_areas), 2)
        if risk_areas
        else 0.0
    )

    # Alerts scoped to the caller's role (admins/analysts see all).
    if user.role in (Role.SYSTEM_ADMIN, Role.SYSTEM_ANALYST):
        alerts_q = Alert.query
    else:
        alerts_q = Alert.query.filter(Alert.target_role.in_(["ALL", user.role]))
    active_alerts = alerts_q.order_by(Alert.created_at.desc()).limit(10).all()

    recent_events = Event.query.order_by(Event.created_at.desc()).limit(8).all()
    suggested_routes = Route.query.order_by(Route.risk_score.asc()).limit(5).all()

    return jsonify(
        user=user.to_dict(include_institution=True),
        kpis={
            "total_events": total_events,
            "total_routes": total_routes,
            "monitored_areas": len(risk_areas),
            "high_risk_areas": len(high_risk),
            "active_alerts": alerts_q.count(),
            "average_risk": avg_risk,
        },
        risk_areas=[a.to_dict() for a in risk_areas[:10]],
        active_alerts=[a.to_dict() for a in active_alerts],
        recent_events=[e.to_dict() for e in recent_events],
        suggested_routes=[r.to_dict(include_geojson=False) for r in suggested_routes],
    )
