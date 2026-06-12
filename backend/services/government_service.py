"""City-wide safety intelligence for GOVERNMENT_AUTHORITY users."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta

from models.event import Event
from models.institution import Institution
from models.risk import RiskArea
from services import gazetteer
from utils.rbac import Role

UNREST_KEYWORDS = ("protest", "unrest", "riot", "violence", "block", "closure", "emergency", "evacuation")
CITY_NAME = "City of Tshwane / Pretoria Metro"


def require_government(user):
    if user is None:
        raise ValueError("Authentication required.")
    if user.role not in (Role.GOVERNMENT_AUTHORITY, Role.SYSTEM_ADMIN):
        raise ValueError("Government portal is for Government Authorities only.")


def _city_institution(user) -> Institution | None:
    if user.institution_id:
        return Institution.query.get(user.institution_id)
    return None


def city_risk_summary() -> dict:
    areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    safe = [a for a in areas if a.risk_level == "LOW"]
    medium = [a for a in areas if a.risk_level == "MEDIUM"]
    high = [a for a in areas if a.risk_level in ("HIGH", "CRITICAL")]
    avg = round(sum(a.risk_score for a in areas) / len(areas), 2) if areas else 0.0
    peak = max((a.risk_score for a in areas), default=0.0)

    if peak >= 85:
        city_level = "CRITICAL"
    elif peak >= 70:
        city_level = "HIGH"
    elif avg >= 40:
        city_level = "MEDIUM"
    else:
        city_level = "LOW"

    return {
        "city_level": city_level,
        "average_risk": avg,
        "peak_risk": round(peak, 2),
        "total_zones": len(areas),
        "safe_zones": len(safe),
        "medium_zones": len(medium),
        "high_risk_zones": len(high),
        "zones": {
            "safe": [a.to_dict() for a in safe],
            "medium": [a.to_dict() for a in medium],
            "high": [a.to_dict() for a in high],
        },
    }


def critical_incidents(limit: int = 12) -> list[Event]:
    return (
        Event.query.filter(Event.severity >= 4)
        .order_by(Event.created_at.desc())
        .limit(limit)
        .all()
    )


def live_incidents(limit: int = 30) -> list[Event]:
    return Event.query.order_by(Event.created_at.desc()).limit(limit).all()


def _is_unrest_event(ev: Event) -> bool:
    text = f"{ev.title} {ev.description or ''} {ev.location}".lower()
    return any(kw in text for kw in UNREST_KEYWORDS)


def unrest_patterns() -> dict:
    """Protest clusters, hotspots, and escalation trends."""
    events = Event.query.order_by(Event.created_at.desc()).limit(100).all()
    unrest = [e for e in events if _is_unrest_event(e)]

    # Hotspots by location
    by_location: dict[str, list] = defaultdict(list)
    for e in unrest:
        by_location[e.location].append(e)

    hotspots = sorted(
        [
            {
                "location": loc,
                "incident_count": len(evs),
                "max_severity": max(e.severity for e in evs),
                "avg_severity": round(sum(e.severity for e in evs) / len(evs), 1),
                "latest": evs[0].to_dict(),
                "events": [e.to_dict() for e in evs[:5]],
            }
            for loc, evs in by_location.items()
        ],
        key=lambda h: (h["incident_count"], h["max_severity"]),
        reverse=True,
    )[:8]

    # 14-day escalation trend
    since = datetime.utcnow() - timedelta(days=14)
    daily_all = defaultdict(int)
    daily_unrest = defaultdict(int)
    for e in events:
        if e.created_at < since:
            continue
        day = e.created_at.strftime("%Y-%m-%d")
        daily_all[day] += 1
        if _is_unrest_event(e):
            daily_unrest[day] += 1

    trend = []
    for i in range(13, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        trend.append({"date": d, "all_incidents": daily_all[d], "unrest_incidents": daily_unrest[d]})

    escalating = daily_unrest.get(datetime.utcnow().strftime("%Y-%m-%d"), 0) > 1

    return {
        "unrest_event_count": len(unrest),
        "protest_clusters": hotspots,
        "escalation_trend": trend,
        "escalation_active": escalating,
    }


def response_decisions(city_risk: dict, patterns: dict, critical: list) -> list[dict]:
    """Advisory coordination actions — government decides, system suggests."""
    decisions = []
    level = city_risk["city_level"]

    if level in ("CRITICAL", "HIGH"):
        decisions.append({
            "type": "police",
            "title": "Consider increased police deployment",
            "detail": f"City risk is {level}. {city_risk['high_risk_zones']} high-risk zone(s) active.",
            "urgency": "critical" if level == "CRITICAL" else "high",
        })
        decisions.append({
            "type": "road_closure",
            "title": "Evaluate road closures in affected corridors",
            "detail": "Multiple incidents may require temporary road network restrictions.",
            "urgency": "high",
        })

    if patterns.get("escalation_active"):
        decisions.append({
            "type": "emergency",
            "title": "Activate emergency coordination protocol",
            "detail": "Unrest incidents are escalating today across multiple zones.",
            "urgency": "critical",
        })

    if patterns.get("protest_clusters"):
        top = patterns["protest_clusters"][0]
        decisions.append({
            "type": "hotspot",
            "title": f"Focus response on {top['location']}",
            "detail": f"{top['incident_count']} unrest-related incident(s), max severity {top['max_severity']}/5.",
            "urgency": "high",
        })

    if len(critical) >= 2:
        decisions.append({
            "type": "broadcast",
            "title": "Issue city-wide public safety warning",
            "detail": "Multiple high-severity incidents active — review and communicate guidance.",
            "urgency": "critical",
        })

    if not decisions:
        decisions.append({
            "type": "monitor",
            "title": "Continue city-wide monitoring",
            "detail": "No immediate escalation detected. Maintain standard disaster management readiness.",
            "urgency": "low",
        })

    return decisions


def city_safety_report() -> dict:
    risk = city_risk_summary()
    patterns = unrest_patterns()
    events = live_incidents(50)
    day_ago = datetime.utcnow() - timedelta(days=1)
    week_ago = datetime.utcnow() - timedelta(days=7)

    return {
        "city": CITY_NAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "city_risk": risk,
        "unrest_patterns": patterns,
        "daily_summary": {
            "incidents": len([e for e in events if e.created_at >= day_ago]),
            "high_severity": len([e for e in events if e.created_at >= day_ago and e.severity >= 4]),
        },
        "weekly_summary": {
            "incidents": len([e for e in events if e.created_at >= week_ago]),
            "unrest_incidents": patterns["unrest_event_count"],
        },
        "incident_breakdown": {
            str(s): len([e for e in events if e.severity == s])
            for s in range(1, 6)
        },
        "top_risk_areas": risk["zones"]["high"][:10],
        "recent_incidents": [e.to_dict() for e in events[:15]],
    }


def dashboard_payload(user) -> dict:
    require_government(user)
    inst = _city_institution(user)
    city_risk = city_risk_summary()
    patterns = unrest_patterns()
    critical = critical_incidents()
    incidents = live_incidents(20)
    decisions = response_decisions(city_risk, patterns, critical)

    return {
        "city": CITY_NAME,
        "department": inst.to_dict() if inst else None,
        "city_risk": city_risk,
        "critical_incidents": [e.to_dict() for e in critical],
        "unrest_patterns": patterns,
        "response_decisions": decisions,
        "live_incidents": [e.to_dict() for e in incidents],
        "map_center": gazetteer.DEFAULT_MAP_CENTER,
        "cities": gazetteer.CITY_MARKERS,
    }


def map_payload(user) -> dict:
    require_government(user)
    areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    events = Event.query.order_by(Event.created_at.desc()).limit(50).all()
    return {
        "map_center": {"lng": 28.1881, "lat": -25.7461, "zoom": 10},
        "cities": gazetteer.CITY_MARKERS,
        "risk_areas": [a.to_dict() for a in areas],
        "incidents": [e.to_dict() for e in events],
    }
