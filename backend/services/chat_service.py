"""Safety Assistant — answers user questions using live platform data."""
from __future__ import annotations

import re

from models.alert import Alert
from models.event import Event
from models.risk import RiskArea
from models.route import Route
from services import route_optimizer
from utils.rbac import Role


def _level_advice(level: str) -> str:
    tips = {
        "LOW": "Conditions look calm. Stay aware of your surroundings.",
        "MEDIUM": "Exercise caution and check alerts before traveling.",
        "HIGH": "Avoid non-essential travel if possible. Use Safe Routes for alternatives.",
        "CRITICAL": "Avoid this area. Follow official alerts and seek safer corridors.",
    }
    return tips.get(level, tips["MEDIUM"])


def _gather_context(user) -> dict:
    risk_areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(8).all()

    if user.role in (Role.SYSTEM_ADMIN, Role.SYSTEM_ANALYST):
        alerts_q = Alert.query
    else:
        alerts_q = Alert.query.filter(Alert.target_role.in_(["ALL", user.role]))
    active_alerts = alerts_q.order_by(Alert.created_at.desc()).limit(8).all()
    routes = Route.query.order_by(Route.risk_score.asc()).limit(5).all()

    avg_risk = (
        round(sum(a.risk_score for a in risk_areas) / len(risk_areas), 1)
        if risk_areas
        else 0.0
    )

    return {
        "risk_areas": [a.to_dict() for a in risk_areas],
        "events": [e.to_dict() for e in recent_events],
        "alerts": [a.to_dict() for a in active_alerts],
        "routes": [r.to_dict() for r in routes],
        "avg_risk": avg_risk,
    }


def _match_area(text: str, areas: list) -> dict | None:
    lower = text.lower()
    for area in areas:
        name = area["area_name"].lower()
        if name in lower or any(part in lower for part in name.split() if len(part) > 3):
            return area
    return None


def _format_area(area: dict) -> str:
    return (
        f"**{area['area_name']}** — risk score **{area['risk_score']}/100** "
        f"({area['risk_level']}).\n{_level_advice(area['risk_level'])}"
    )


def answer(message: str, user) -> dict:
    """Return assistant reply text and optional quick-action hints."""
    text = (message or "").strip()
    if not text:
        return {"reply": "Ask me about area safety, active alerts, recent incidents, or safe routes."}

    lower = text.lower()
    ctx = _gather_context(user)
    areas = ctx["risk_areas"]
    events = ctx["events"]
    alerts = ctx["alerts"]

    # Greetings / help
    if re.search(r"\b(hi|hello|hey|help|what can you)\b", lower):
        return {
            "reply": (
                "I'm your **SafeRoute Safety Assistant**. I use live data from the platform.\n\n"
                "You can ask me things like:\n"
                "• \"Is it safe to travel to Umlazi?\"\n"
                "• \"Is Durban CBD safe today?\"\n"
                "• \"What route is safe to UKZN?\"\n"
                "• \"What alerts are active?\"\n"
                "• \"Which areas are most dangerous?\""
            ),
            "suggestions": ["Active alerts", "Safest areas", "Recent incidents"],
        }

    # Safe route guidance — try to answer origin→destination questions
    if re.search(r"\b(route|travel|go to|get to|directions|navigate|safest way)\b", lower):
        dest_match = re.search(
            r"(?:to|towards?|into)\s+([a-z0-9\s\-]+?)(?:\?|$|\.|,| from)",
            lower,
        )
        origin_match = re.search(
            r"(?:from)\s+([a-z0-9\s\-]+?)(?:\s+to|\?|$|\.|,)",
            lower,
        )
        dest = dest_match.group(1).strip().title() if dest_match else None
        origin = origin_match.group(1).strip().title() if origin_match else None

        if dest and origin:
            try:
                result = route_optimizer.generate_route(origin, dest)
                alts = result.get("alternatives") or []
                alt_text = ""
                if alts:
                    alt_text = "\n\nAlternatives:\n" + "\n".join(
                        f"• {a.get('label', 'Alt')}: risk {a['risk_score']}/100 — {a.get('explanation', '')}"
                        for a in alts[:2]
                    )
                return {
                    "reply": (
                        f"**{origin} → {dest}**\n"
                        f"Safest route risk: **{result['risk_score']}/100** ({result.get('risk_level', 'SAFE')}).\n"
                        f"{result.get('explanation', '')}"
                        + alt_text
                    ),
                    "action": {"label": "View on map", "href": "/routes"},
                }
            except Exception:
                pass

        safest = ctx["routes"][0] if ctx["routes"] else None
        extra = ""
        if safest:
            extra = (
                f"\n\nLowest-risk saved route: **{safest['start_location']} → "
                f"{safest['end_location']}** (risk {safest['risk_score']}/100)."
            )
        return {
            "reply": (
                "Open **Safe Routes**, enter your origin and destination "
                "(e.g. Durban Station → UKZN), and I'll find the safest road corridor "
                "using live incident and risk-zone data."
                + extra
            ),
            "action": {"label": "Open Safe Routes", "href": "/routes"},
        }

    # Alerts
    if re.search(r"\b(alert|warning|broadcast|notify)\b", lower):
        if not alerts:
            return {"reply": "There are **no active alerts** for your account right now. Conditions may still change — check back often."}
        lines = [
            f"• [{a['severity']}] {a['message']}" for a in alerts[:5]
        ]
        return {
            "reply": f"**{len(alerts)} alert(s)** relevant to you:\n\n" + "\n".join(lines),
            "action": {"label": "View all alerts", "href": "/alerts"},
        }

    # Events / incidents / what's happening
    if re.search(r"\b(event|incident|happening|news|protest|accident|unrest|report)\b", lower):
        matched = [e for e in events if e["location"].lower() in lower or e["title"].lower() in lower]
        pool = matched if matched else events
        if not pool:
            return {"reply": "No recent incidents are recorded in the system right now."}
        lines = [
            f"• **{e['title']}** ({e['location']}) — severity {e['severity']}/5"
            for e in pool[:5]
        ]
        intro = "Recent incidents matching your question:" if matched else "Latest incidents across the city:"
        return {
            "reply": intro + "\n\n" + "\n".join(lines),
            "action": {"label": "View incidents", "href": "/events"},
        }

    # Safest / dangerous areas
    if re.search(r"\b(safest|safe area|low risk|green zone)\b", lower):
        safe = [a for a in areas if a["risk_level"] in ("LOW", "MEDIUM")][:3]
        if not safe:
            return {"reply": "No low-risk areas are listed yet. Check the **Safety Map** for updates."}
        return {
            "reply": "Areas with lower risk right now:\n\n" + "\n\n".join(_format_area(a) for a in safe),
            "action": {"label": "Open Safety Map", "href": "/map"},
        }

    if re.search(r"\b(dangerous|high risk|unsafe|worst|critical|avoid)\b", lower):
        risky = [a for a in areas if a["risk_level"] in ("HIGH", "CRITICAL")][:4]
        if not risky:
            return {"reply": "No high-risk areas are flagged right now. City-wide average risk is **{:.0f}/100**.".format(ctx["avg_risk"])}
        return {
            "reply": "Higher-risk areas to watch:\n\n" + "\n\n".join(_format_area(a) for a in risky),
            "action": {"label": "Open Safety Map", "href": "/map"},
        }

    # Specific area lookup
    area = _match_area(text, areas)
    if area:
        related_events = [e for e in events if area["area_name"].lower() in e["location"].lower()]
        reply = _format_area(area)
        if related_events:
            reply += "\n\nRecent incidents nearby:\n" + "\n".join(
                f"• {e['title']} (sev {e['severity']})" for e in related_events[:3]
            )
        return {"reply": reply, "action": {"label": "View on map", "href": "/map"}}

    # Safety / is X safe
    if re.search(r"\b(safe|safety|risk|score)\b", lower):
        if areas:
            top = areas[0]
            return {
                "reply": (
                    f"City-wide average risk is **{ctx['avg_risk']}/100**.\n\n"
                    f"Highest monitored area: **{top['area_name']}** at {top['risk_score']}/100 ({top['risk_level']}).\n"
                    f"{_level_advice(top['risk_level'])}"
                ),
                "suggestions": ["Active alerts", "Safest areas", "Recent incidents"],
            }

    # Default summary
    summary_parts = [f"City average risk: **{ctx['avg_risk']}/100**."]
    if alerts:
        summary_parts.append(f"**{len(alerts)}** active alert(s).")
    if events:
        summary_parts.append(f"Latest incident: **{events[0]['title']}** in {events[0]['location']}.")
    if areas:
        summary_parts.append(f"Highest-risk area: **{areas[0]['area_name']}** ({areas[0]['risk_level']}).")

    summary_parts.append(
        "\nTry asking about a specific area (e.g. \"Umlazi\" or \"Durban CBD\"), alerts, incidents, or safe routes."
    )
    return {
        "reply": " ".join(summary_parts[:4]) + summary_parts[-1],
        "suggestions": ["Is Umlazi safe?", "Route to UKZN", "Active alerts"],
    }
