"""Institution-scoped safety intelligence for INSTITUTION_ADMIN users."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from models.event import Event
from models.institution import Institution
from models.risk import RiskArea
from models.route import Route
from models.user import User
from services import gazetteer, route_optimizer
from services.geo_service import haversine_km
from utils.rbac import Role


def require_institution(user) -> Institution:
    """Return the caller's institution or raise ValueError."""
    if user is None or not user.institution_id:
        raise ValueError("No institution linked to your account.")
    inst = Institution.query.get(user.institution_id)
    if inst is None:
        raise ValueError("Institution record not found.")
    return inst


def institution_coords(inst: Institution) -> tuple[float, float]:
    """Return (longitude, latitude) for an institution."""
    if inst.longitude is not None and inst.latitude is not None:
        return (inst.longitude, inst.latitude)
    return gazetteer.coord_for(inst.location or inst.name)


def sync_institution_coords(inst: Institution) -> None:
    lon, lat = institution_coords(inst)
    inst.longitude = lon
    inst.latitude = lat
    if inst.radius_km is None:
        inst.radius_km = gazetteer.radius_for(inst.location or inst.name)


def _radius_km(inst: Institution) -> float:
    return inst.radius_km or 8.0


def nearby_events(inst: Institution, limit: int = 30) -> list[Event]:
    radius = _radius_km(inst)
    lon, lat = institution_coords(inst)
    results = []
    for ev in Event.query.filter(Event.latitude.isnot(None)).order_by(Event.created_at.desc()).all():
        if haversine_km(lat, lon, ev.latitude, ev.longitude) <= radius:
            results.append(ev)
        if len(results) >= limit:
            break
    return results


def nearby_risk_areas(inst: Institution) -> list[RiskArea]:
    radius = _radius_km(inst)
    lon, lat = institution_coords(inst)
    areas = []
    loc_key = (inst.location or "").lower()
    for area in RiskArea.query.all():
        if loc_key and loc_key in (area.area_name or "").lower():
            areas.append(area)
            continue
        if area.latitude is None or area.longitude is None:
            continue
        if haversine_km(lat, lon, area.latitude, area.longitude) <= radius + (area.radius_km or 2.5):
            areas.append(area)
    return sorted(areas, key=lambda a: a.risk_score, reverse=True)


def institution_alerts(user, inst: Institution, limit: int = 10) -> list[Event]:
    """High-severity incidents near the institution (legacy key for portal UI)."""
    return [e for e in nearby_events(inst, limit=limit * 2) if e.severity >= 3][:limit]


def institution_routes(inst: Institution, limit: int = 10) -> list[Route]:
    """Routes that start or end near the institution."""
    radius = _radius_km(inst) + 2.0
    lon, lat = institution_coords(inst)
    loc_key = (inst.location or "").lower()
    routes = []
    for r in Route.query.order_by(Route.created_at.desc()).all():
        match = False
        if loc_key and (loc_key in (r.start_location or "").lower() or loc_key in (r.end_location or "").lower()):
            match = True
        if r.start_lat is not None and haversine_km(lat, lon, r.start_lat, r.start_lng) <= radius:
            match = True
        if r.end_lat is not None and haversine_km(lat, lon, r.end_lat, r.end_lng) <= radius:
            match = True
        if match:
            routes.append(r)
        if len(routes) >= limit:
            break
    return routes


def compute_campus_risk(inst: Institution) -> dict:
    """Aggregate risk level for the institution's surrounding area."""
    areas = nearby_risk_areas(inst)
    events = nearby_events(inst, limit=50)
    if areas:
        avg = sum(a.risk_score for a in areas) / len(areas)
        peak = max(a.risk_score for a in areas)
        level = areas[0].risk_level if areas else "LOW"
        if peak >= 85:
            level = "CRITICAL"
        elif peak >= 70:
            level = "HIGH"
        elif avg >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"
    elif events:
        avg_sev = sum(e.severity for e in events) / len(events)
        avg = min(100, avg_sev * 20)
        level = "HIGH" if avg >= 70 else "MEDIUM" if avg >= 40 else "LOW"
        peak = avg
    else:
        avg, peak, level = 15.0, 15.0, "LOW"

    return {
        "risk_score": round(avg, 2),
        "peak_risk": round(peak, 2),
        "risk_level": level,
        "monitored_areas": len(areas),
        "nearby_incidents": len(events),
    }


def safety_trend(inst: Institution, days: int = 7) -> list[dict]:
    """Daily incident counts near institution for the past N days."""
    since = datetime.utcnow() - timedelta(days=days)
    radius = _radius_km(inst)
    lon, lat = institution_coords(inst)
    buckets = defaultdict(int)
    for ev in Event.query.filter(Event.created_at >= since).all():
        if ev.latitude is None:
            continue
        if haversine_km(lat, lon, ev.latitude, ev.longitude) > radius:
            continue
        day = ev.created_at.strftime("%Y-%m-%d")
        buckets[day] += 1
    trend = []
    for i in range(days - 1, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        trend.append({"date": d, "incidents": buckets.get(d, 0)})
    return trend


def operational_decisions(inst: Institution, campus_risk: dict, incidents: list, events: list) -> list[dict]:
    """Suggested operational actions — advisory only, admin decides."""
    level = campus_risk["risk_level"]
    decisions = []
    critical_events = [e for e in events if e.severity >= 4]

    if level == "CRITICAL":
        decisions.append({
            "type": "evacuation",
            "title": "Consider evacuation or shelter-in-place",
            "detail": "Critical risk near campus. Review SAPS guidance and suspend on-site activities if needed.",
            "urgency": "critical",
        })
        decisions.append({
            "type": "suspend",
            "title": "Suspend classes / on-site work",
            "detail": "Move to remote operations until the situation stabilises.",
            "urgency": "critical",
        })
    elif level == "HIGH":
        decisions.append({
            "type": "remote",
            "title": "Consider remote work / online classes",
            "detail": "High-risk incidents nearby. Reduce foot traffic on campus.",
            "urgency": "high",
        })
        decisions.append({
            "type": "schedule",
            "title": "Review schedule changes",
            "detail": "Stagger arrivals and avoid peak protest hours near campus corridors.",
            "urgency": "high",
        })
    elif level == "MEDIUM":
        decisions.append({
            "type": "monitor",
            "title": "Increase monitoring — operate with caution",
            "detail": "Some incidents nearby. Brief staff and students on safe routes.",
            "urgency": "medium",
        })
    else:
        decisions.append({
            "type": "normal",
            "title": "Normal operations recommended",
            "detail": "Campus surroundings appear calm. Continue standard safety protocols.",
            "urgency": "low",
        })

    if critical_events:
        decisions.append({
            "type": "commute",
            "title": "Review staff/student commute routes",
            "detail": f"{len(critical_events)} high-severity incident(s) near campus — use Safe Routes for alternatives.",
            "urgency": "high",
        })

    if len(incidents) >= 2:
        decisions.append({
            "type": "incident",
            "title": "Multiple incidents affecting your institution area",
            "detail": "Review nearby events and communicate guidance to staff/students.",
            "urgency": "high",
        })

    return decisions


def safe_commute_routes(inst: Institution) -> list[dict]:
    """Generate safe route suggestions toward the institution from key nearby points."""
    loc = inst.location or inst.name
    origins = []
    if "ukzn" in loc.lower() or "westville" in loc.lower():
        origins = ["Pretoria Station", "Hatfield", "Soshanguve"]
    elif "durban" in loc.lower():
        origins = ["Umhlanga", "Pinetown", "Chatsworth"]
    elif "johannesburg" in loc.lower():
        origins = ["Sandton", "Soweto"]
    elif "cape town" in loc.lower():
        origins = ["Bellville", "Khayelitsha"]
    else:
        origins = ["Pretoria Station", "Hatfield"]

    suggestions = []
    for origin in origins[:3]:
        try:
            result = route_optimizer.generate_route(origin, loc)
            suggestions.append({
                "from": origin,
                "to": loc,
                "risk_score": result["risk_score"],
                "risk_level": result.get("risk_level"),
                "explanation": result.get("explanation", ""),
            })
        except Exception:
            pass
    return sorted(suggestions, key=lambda s: s["risk_score"])


def build_report(inst: Institution) -> dict:
    """Daily and weekly safety summary for download."""
    events = nearby_events(inst, limit=100)
    campus = compute_campus_risk(inst)
    week_ago = datetime.utcnow() - timedelta(days=7)
    day_ago = datetime.utcnow() - timedelta(days=1)
    weekly = [e for e in events if e.created_at >= week_ago]
    daily = [e for e in events if e.created_at >= day_ago]

    return {
        "institution": inst.to_dict(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "campus_risk": campus,
        "daily_summary": {
            "incidents": len(daily),
            "high_severity": len([e for e in daily if e.severity >= 4]),
            "events": [e.to_dict() for e in daily[:10]],
        },
        "weekly_summary": {
            "incidents": len(weekly),
            "high_severity": len([e for e in weekly if e.severity >= 4]),
            "events": [e.to_dict() for e in weekly[:20]],
        },
        "trend": safety_trend(inst, days=14),
        "risk_areas": [a.to_dict() for a in nearby_risk_areas(inst)],
    }


def dashboard_payload(user) -> dict:
    inst = require_institution(user)
    sync_institution_coords(inst)
    campus = compute_campus_risk(inst)
    events = nearby_events(inst)
    alerts = institution_alerts(user, inst)
    areas = nearby_risk_areas(inst)
    routes = institution_routes(inst)
    decisions = operational_decisions(inst, campus, alerts, events)

    safe_zones = [a.to_dict() for a in areas if a.risk_level in ("LOW", "MEDIUM")]
    danger_zones = [a.to_dict() for a in areas if a.risk_level in ("HIGH", "CRITICAL")]

    return {
        "institution": inst.to_dict(),
        "campus_risk": campus,
        "safety_trend": safety_trend(inst),
        "nearby_incidents": [e.to_dict() for e in events[:12]],
        "institution_alerts": [e.to_dict() for e in alerts],
        "safe_zones": safe_zones,
        "danger_zones": danger_zones,
        "operational_decisions": decisions,
        "commute_routes": safe_commute_routes(inst),
        "institution_routes": [r.to_dict() for r in routes],
        "staff_count": inst.staff_count or 0,
        "student_count": inst.student_count or 0,
        "user_count": User.query.filter_by(institution_id=inst.id).count(),
    }


def map_payload(user) -> dict:
    inst = require_institution(user)
    sync_institution_coords(inst)
    lon, lat = institution_coords(inst)
    radius = _radius_km(inst)
    events = nearby_events(inst, limit=50)
    areas = nearby_risk_areas(inst)
    alerts = institution_alerts(user, inst, limit=15)

    return {
        "map_center": {"lng": lon, "lat": lat, "zoom": 13},
        "institution": {
            **inst.to_dict(),
            "latitude": lat,
            "longitude": lon,
            "radius_km": radius,
        },
        "risk_areas": [a.to_dict() for a in areas],
        "incidents": [e.to_dict() for e in events],
        "commute_routes": safe_commute_routes(inst),
    }
