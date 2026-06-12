"""Dashboard summary endpoint feeding the KPI cards and feeds."""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from sqlalchemy import func

from extensions import db
from logger import get_logger
from models.event import Event
from models.route import Route
from models.risk import RiskArea
from utils.rbac import Role, require_roles, current_user

bp = Blueprint("dashboard", __name__)
log = get_logger(__name__)

_CATEGORY_KEYWORDS = (
    ("Theft", ("theft", "rob", "burgl", "stolen", "mugging")),
    ("Assault", ("assault", "attack", "violence", "fight")),
    ("Accident", ("accident", "crash", "collision", "hit-and-run")),
    ("Vandalism", ("vandal", "graffiti", "damage", "arson")),
)


def _event_category(title: str) -> str:
    text = (title or "").lower()
    for label, words in _CATEGORY_KEYWORDS:
        if any(word in text for word in words):
            return label
    return "Other"


def _day_risk_score(events, fallback: float) -> int:
    if not events:
        return int(round(fallback))
    avg_sev = sum(e.severity for e in events) / len(events)
    return min(100, int(round(avg_sev * 16 + len(events) * 4)))


@bp.get("/summary")
@require_roles(*Role.all())
def summary():
    user = current_user()
    try:
        total_events = Event.query.count()
        total_routes = Route.query.count()
        high_severity_events = Event.query.filter(Event.severity >= 4).count()

        avg_risk = db.session.query(func.avg(RiskArea.risk_score)).scalar() or 0.0
        monitored_areas = RiskArea.query.count()
        high_risk_areas = RiskArea.query.filter(RiskArea.risk_score >= 70).count()

        top_risk_areas = (
            RiskArea.query.order_by(RiskArea.risk_score.desc()).limit(10).all()
        )

        recent_events = Event.query.order_by(Event.created_at.desc()).limit(10).all()
        suggested_routes = Route.query.order_by(Route.risk_score.asc()).limit(5).all()

        today = datetime.utcnow().date()
        risk_trend = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            day_events = Event.query.filter(
                Event.created_at >= day_start, Event.created_at < day_end
            ).all()
            risk_trend.append(
                {
                    "label": day.strftime("%a"),
                    "score": _day_risk_score(day_events, float(avg_risk)),
                }
            )

        heatmap = []
        for offset in range(27, -1, -1):
            day = today - timedelta(days=offset)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            count = Event.query.filter(
                Event.created_at >= day_start, Event.created_at < day_end
            ).count()
            heatmap.append(
                {
                    "label": f"{day.strftime('%a')} {day.strftime('%b %d')}",
                    "count": count,
                }
            )

        category_counts = {label: 0 for label, _ in _CATEGORY_KEYWORDS}
        category_counts["Other"] = 0
        for (title,) in db.session.query(Event.title).all():
            category_counts[_event_category(title)] += 1

        safe_routes = Route.query.filter(Route.risk_score < 40).count()
        safety_score = max(0, min(100, int(round(100 - float(avg_risk)))))

        return jsonify(
            user=user.to_dict(),
            kpis={
                "total_events": total_events,
                "total_routes": total_routes,
                "monitored_areas": monitored_areas,
                "high_risk_areas": high_risk_areas,
                "high_severity_events": high_severity_events,
                "average_risk": round(float(avg_risk), 2),
                "safe_routes": safe_routes,
                "safety_score": safety_score,
            },
            risk_areas=[a.to_dict() for a in top_risk_areas],
            recent_events=[e.to_dict() for e in recent_events],
            suggested_routes=[r.to_dict(include_geojson=False) for r in suggested_routes],
            analytics={
                "risk_trend": risk_trend,
                "heatmap": heatmap,
                "categories": category_counts,
                "coverage_pct": min(100, monitored_areas * 12) if monitored_areas else 0,
                "incident_load_pct": min(
                    100,
                    int(round((high_severity_events / total_events) * 100)) if total_events else 0,
                ),
                "route_safety_pct": min(
                    100,
                    int(round((safe_routes / total_routes) * 100)) if total_routes else 0,
                ),
            },
        )
    except Exception:
        log.exception("Dashboard summary failed for user %s", getattr(user, "email", None))
        db.session.rollback()
        return jsonify(error="Dashboard temporarily unavailable. Please retry."), 503
