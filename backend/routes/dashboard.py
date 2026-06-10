"""Dashboard summary endpoint feeding the KPI cards and feeds."""
from flask import Blueprint, jsonify

from sqlalchemy import func

from extensions import db
from logger import get_logger
from models.event import Event
from models.alert import Alert
from models.route import Route
from models.risk import RiskArea
from utils.rbac import Role, require_roles, current_user

bp = Blueprint("dashboard", __name__)
log = get_logger(__name__)


@bp.get("/summary")
@require_roles(*Role.all())
def summary():
    user = current_user()
    try:
        total_events = Event.query.count()
        total_routes = Route.query.count()

        avg_risk = db.session.query(func.avg(RiskArea.risk_score)).scalar() or 0.0
        monitored_areas = RiskArea.query.count()
        high_risk_areas = RiskArea.query.filter(RiskArea.risk_score >= 70).count()

        top_risk_areas = (
            RiskArea.query.order_by(RiskArea.risk_score.desc()).limit(10).all()
        )

        if user.role in (Role.SYSTEM_ADMIN, Role.SYSTEM_ANALYST):
            alerts_q = Alert.query
        else:
            alerts_q = Alert.query.filter(Alert.target_role.in_(["ALL", user.role]))

        active_alerts_count = alerts_q.count()
        active_alerts = alerts_q.order_by(Alert.created_at.desc()).limit(10).all()
        recent_events = Event.query.order_by(Event.created_at.desc()).limit(8).all()
        suggested_routes = Route.query.order_by(Route.risk_score.asc()).limit(5).all()

        return jsonify(
            user=user.to_dict(include_institution=True),
            kpis={
                "total_events": total_events,
                "total_routes": total_routes,
                "monitored_areas": monitored_areas,
                "high_risk_areas": high_risk_areas,
                "active_alerts": active_alerts_count,
                "average_risk": round(float(avg_risk), 2),
            },
            risk_areas=[a.to_dict() for a in top_risk_areas],
            active_alerts=[a.to_dict() for a in active_alerts],
            recent_events=[e.to_dict() for e in recent_events],
            suggested_routes=[r.to_dict(include_geojson=False) for r in suggested_routes],
        )
    except Exception as exc:
        log.exception("Dashboard summary failed for user %s", getattr(user, "email", None))
        db.session.rollback()
        return jsonify(error="Dashboard temporarily unavailable. Please retry."), 503
