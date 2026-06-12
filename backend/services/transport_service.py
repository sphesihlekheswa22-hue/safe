"""Transport-operator safety intelligence — routes, fleet, and corridor risk."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from models.event import Event
from models.institution import Institution
from models.route import Route
from models.user import User
from services import gazetteer, route_optimizer, geocoding_service
from services.geo_service import haversine_km
from data.transport_fleet import DEMO_FLEET, KEY_CORRIDORS
from utils.rbac import Role


TRANSPORT_KEYWORDS = (
    "road", "route", "n3", "n2", "block", "closure", "protest", "taxi",
    "traffic", "accident", "unrest", "reroute", "transport", "highway",
)


def _risk_level(score: float) -> str:
    if score >= 70:
        return "DANGEROUS"
    if score >= 40:
        return "WARNING"
    return "SAFE"


def _route_status(route: dict) -> dict:
    score = route.get("risk_score", 0)
    level = _risk_level(score)
    color = "green" if level == "SAFE" else "yellow" if level == "WARNING" else "red"
    return {**route, "risk_level": level, "status_color": color}


def require_transport_operator(user) -> Institution:
    if user is None:
        raise ValueError("Authentication required.")
    if user.role not in (Role.TRANSPORT_OPERATOR, Role.SYSTEM_ADMIN):
        raise ValueError("Transport portal is for Transport Operators only.")
    if not user.institution_id:
        raise ValueError("No transport company linked to your account.")
    inst = Institution.query.get(user.institution_id)
    if inst is None:
        raise ValueError("Transport company record not found.")
    return inst


def operator_coords(inst: Institution) -> tuple[float, float]:
    if inst.longitude is not None and inst.latitude is not None:
        return (inst.longitude, inst.latitude)
    return gazetteer.coord_for(inst.location or inst.name)


def _metro_radius(inst: Institution) -> float:
    return inst.radius_km or 25.0


def transport_alerts(user, inst: Institution, limit: int = 15) -> list[Event]:
    """Recent transport-relevant incidents near the operator (legacy portal key)."""
    return transport_incidents(inst, limit=limit)


def transport_incidents(inst: Institution, limit: int = 25) -> list[Event]:
    radius = _metro_radius(inst)
    lon, lat = operator_coords(inst)
    results = []
    for ev in Event.query.filter(Event.latitude.isnot(None)).order_by(Event.created_at.desc()).all():
        if haversine_km(lat, lon, ev.latitude, ev.longitude) <= radius:
            results.append(ev)
        if len(results) >= limit:
            break
    return results


def corridor_safety() -> list[dict]:
    """Evaluate key transport corridors for current safety status."""
    corridors = []
    for start, end in KEY_CORRIDORS:
        try:
            result = route_optimizer.generate_route(start, end)
            corridors.append(_route_status({
                "corridor": f"{start} → {end}",
                "start_location": start,
                "end_location": end,
                "risk_score": result["risk_score"],
                "risk_level": result.get("risk_level", _risk_level(result["risk_score"])),
                "explanation": result.get("explanation", ""),
                "geojson": result.get("geojson"),
            }))
        except Exception:
            corridors.append({
                "corridor": f"{start} → {end}",
                "start_location": start,
                "end_location": end,
                "risk_score": 50.0,
                "risk_level": "WARNING",
                "status_color": "yellow",
                "explanation": "Could not evaluate corridor.",
            })
    return sorted(corridors, key=lambda c: c["risk_score"])


def saved_routes_status(limit: int = 20) -> list[dict]:
    routes = Route.query.order_by(Route.created_at.desc()).limit(limit).all()
    return [_route_status(r.to_dict()) for r in routes]


def fleet_status(inst: Institution, corridors_list: list[dict] | None = None) -> list[dict]:
    """Monitor demo fleet against corridor risk."""
    corridors = {c["corridor"]: c for c in (corridors_list or corridor_safety())}
    fleet = []
    for vehicle in DEMO_FLEET:
        corridor_key = vehicle["corridor"]
        match = corridors.get(corridor_key)
        if match is None:
            for c in corridors.values():
                if vehicle["corridor"].split(" → ")[0] in c["corridor"]:
                    match = c
                    break
        risk = match["risk_score"] if match else 35.0
        level = _risk_level(risk)
        fleet.append({
            **vehicle,
            "risk_score": risk,
            "risk_level": level,
            "status": "HOLD" if level == "DANGEROUS" else "CAUTION" if level == "WARNING" else "CLEAR",
            "advice": match["explanation"] if match else "No corridor data.",
        })
    return fleet


def performance_metrics() -> dict:
    """Track safe vs unsafe route history."""
    routes = Route.query.order_by(Route.created_at.desc()).all()
    safe = warning = dangerous = 0
    for r in routes:
        lvl = _risk_level(r.risk_score)
        if lvl == "SAFE":
            safe += 1
        elif lvl == "WARNING":
            warning += 1
        else:
            dangerous += 1

    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = [r for r in routes if r.created_at >= week_ago]
    blocked_events = Event.query.filter(Event.created_at >= week_ago).all()
    block_count = sum(
        1 for e in blocked_events
        if e.severity >= 3 and any(kw in (e.title + (e.description or "")).lower() for kw in ("block", "closure", "protest"))
    )

    daily = defaultdict(lambda: {"safe": 0, "warning": 0, "dangerous": 0})
    for r in recent:
        day = r.created_at.strftime("%Y-%m-%d")
        lvl = _risk_level(r.risk_score)
        if lvl == "SAFE":
            daily[day]["safe"] += 1
        elif lvl == "WARNING":
            daily[day]["warning"] += 1
        else:
            daily[day]["dangerous"] += 1

    trend = []
    for i in range(6, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        trend.append({"date": d, **daily[d]})

    total = len(routes) or 1
    return {
        "total_routes": len(routes),
        "safe_routes": safe,
        "warning_routes": warning,
        "dangerous_routes": dangerous,
        "safe_ratio_pct": round(safe / total * 100, 1),
        "blocked_incidents_week": block_count,
        "routes_this_week": len(recent),
        "weekly_trend": trend,
    }


def suggest_route(start_location: str, end_location: str, start_lat=None, start_lng=None, end_lat=None, end_lng=None) -> dict:
    start = geocoding_service.resolve_location(start_location, start_lat, start_lng)
    end = geocoding_service.resolve_location(end_location, end_lat, end_lng)
    result = route_optimizer.generate_route(
        start["name"], end["name"],
        start_coord=(start["lng"], start["lat"]),
        end_coord=(end["lng"], end["lat"]),
    )
    best = _route_status({
        "start_location": result["start_location"],
        "end_location": result["end_location"],
        "risk_score": result["risk_score"],
        "risk_level": result.get("risk_level"),
        "explanation": result.get("explanation", ""),
        "geojson": result["geojson"],
        "start_lat": result.get("start_lat"),
        "start_lng": result.get("start_lng"),
        "end_lat": result.get("end_lat"),
        "end_lng": result.get("end_lng"),
    })
    alts = [_route_status({
        "label": a.get("label"),
        "risk_score": a["risk_score"],
        "risk_level": a.get("risk_level"),
        "explanation": a.get("explanation", ""),
        "geojson": a.get("geojson"),
    }) for a in result.get("alternatives", [])]
    return {"route": best, "alternatives": alts}


def dashboard_payload(user) -> dict:
    inst = require_transport_operator(user)
    lon, lat = operator_coords(inst)
    corridors = corridor_safety()
    incidents = transport_incidents(inst)
    alerts = transport_alerts(user, inst)
    performance = performance_metrics()

    safe_corridors = [c for c in corridors if c["risk_level"] == "SAFE"]
    risky_corridors = [c for c in corridors if c["risk_level"] == "WARNING"]
    dangerous_corridors = [c for c in corridors if c["risk_level"] == "DANGEROUS"]

    return {
        "operator": inst.to_dict(),
        "map_center": {"lng": lon, "lat": lat, "zoom": 11},
        "corridor_safety": {
            "safe": safe_corridors,
            "warning": risky_corridors,
            "dangerous": dangerous_corridors,
            "all": corridors,
        },
        "saved_routes": saved_routes_status(),
        "transport_alerts": [e.to_dict() for e in alerts],
        "live_incidents": [e.to_dict() for e in incidents],
        "fleet": fleet_status(inst, corridors),
        "performance": performance,
    }


def map_payload(user) -> dict:
    inst = require_transport_operator(user)
    lon, lat = operator_coords(inst)
    incidents = transport_incidents(inst, limit=40)
    corridors = corridor_safety()
    return {
        "map_center": {"lng": lon, "lat": lat, "zoom": 11},
        "operator": inst.to_dict(),
        "incidents": [e.to_dict() for e in incidents],
        "corridors": corridors,
    }
