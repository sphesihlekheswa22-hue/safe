"""Safety Assistant — answers using live DB context + OpenAI (when configured)."""
from __future__ import annotations

import logging
import re

from models.alert import Alert
from models.event import Event
from models.risk import RiskArea
from models.route import Route
from services import route_optimizer
from services import ai_chat_service
from utils.rbac import Role

logger = logging.getLogger(__name__)


def _level_advice(level: str) -> str:
    tips = {
        "LOW": "Conditions look calm. Stay aware of your surroundings.",
        "MEDIUM": "Exercise caution and check alerts before travelling.",
        "HIGH": "Avoid non-essential travel if possible. Use Safe Routes for alternatives.",
        "CRITICAL": "Avoid this area. Follow official alerts and seek safer corridors.",
    }
    return tips.get(level, tips["MEDIUM"])


def _gather_context(user) -> dict:
    risk_areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(12).all()

    if user.role in (Role.SYSTEM_ADMIN, Role.SYSTEM_ANALYST):
        alerts_q = Alert.query
    else:
        alerts_q = Alert.query.filter(Alert.target_role.in_(["ALL", user.role]))
    active_alerts = alerts_q.order_by(Alert.created_at.desc()).limit(10).all()
    routes = Route.query.order_by(Route.risk_score.asc()).limit(6).all()

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
        "computed_route": None,
    }


def _maybe_compute_route(message: str, ctx: dict) -> None:
    """If the user asks for directions, attach a live OSRM corridor to context."""
    lower = message.lower()
    if not re.search(r"\b(route|travel|go to|get to|directions|navigate|safest way)\b", lower):
        return

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
    if not dest or not origin:
        return

    try:
        result = route_optimizer.generate_route(origin, dest)
        ctx["computed_route"] = {
            "origin": origin,
            "destination": dest,
            "risk_score": result.get("risk_score"),
            "risk_level": result.get("risk_level"),
            "explanation": result.get("explanation"),
            "alternatives": (result.get("alternatives") or [])[:2],
        }
    except Exception as exc:
        logger.info("Route pre-compute for chat skipped: %s", exc)


def _answer_with_rules(message: str, ctx: dict) -> dict:
    """Rule-based fallback when AI is unavailable."""
    text = (message or "").strip()
    lower = text.lower()
    areas = ctx["risk_areas"]
    events = ctx["events"]
    alerts = ctx["alerts"]

    if re.search(r"\b(hi|hello|hey|help|what can you)\b", lower):
        return {
            "reply": (
                "I'm your **SafeRoute Safety Assistant** for South Africa. I use live platform data.\n\n"
                "Ask about areas (Umlazi, Durban CBD, UKZN), **active alerts**, **incidents**, or **safe routes**."
            ),
            "suggestions": ["Is Umlazi safe?", "Active alerts", "Route to UKZN"],
        }

    if ctx.get("computed_route"):
        r = ctx["computed_route"]
        alts = r.get("alternatives") or []
        alt_text = ""
        if alts:
            alt_text = "\n\nAlternatives:\n" + "\n".join(
                f"• {a.get('label', 'Alt')}: risk {a['risk_score']}/100"
                for a in alts
            )
        return {
            "reply": (
                f"**{r['origin']} → {r['destination']}**\n"
                f"Risk: **{r['risk_score']}/100** ({r.get('risk_level', 'SAFE')}).\n"
                f"{r.get('explanation', '')}" + alt_text
            ),
            "action": {"label": "View on map", "href": "/routes"},
        }

    if re.search(r"\b(alert|warning|broadcast)\b", lower):
        if not alerts:
            return {"reply": "No **active alerts** for your role right now."}
        lines = [f"• [{a['severity']}] {a['message']}" for a in alerts[:5]]
        return {
            "reply": f"**{len(alerts)} alert(s)** for you:\n\n" + "\n".join(lines),
            "action": {"label": "View all alerts", "href": "/alerts"},
        }

    if re.search(r"\b(event|incident|happening|protest|unrest)\b", lower):
        if not events:
            return {"reply": "No recent incidents recorded."}
        lines = [f"• **{e['title']}** ({e['location']}) — sev {e['severity']}/5" for e in events[:5]]
        return {
            "reply": "Latest SA incidents:\n\n" + "\n".join(lines),
            "action": {"label": "View incidents", "href": "/events"},
        }

    if areas:
        top = areas[0]
        return {
            "reply": (
                f"City average risk: **{ctx['avg_risk']}/100**.\n"
                f"Highest area: **{top['area_name']}** ({top['risk_score']}/100, {top['risk_level']}).\n"
                f"{_level_advice(top['risk_level'])}"
            ),
            "suggestions": ["Active alerts", "Is Durban CBD safe?", "Safest areas"],
        }

    return {
        "reply": "Ask about a **South African area**, alerts, incidents, or safe routes.",
        "suggestions": ["Is Umlazi safe?", "Active alerts", "Recent incidents"],
    }


def answer(message: str, user) -> dict:
    """Return assistant reply using OpenAI + live DB context, with rule fallback."""
    text = (message or "").strip()
    if not text:
        return {"reply": "Ask me about area safety, alerts, incidents, or safe routes in South Africa."}

    ctx = _gather_context(user)
    _maybe_compute_route(text, ctx)

    if ai_chat_service.is_enabled():
        try:
            return ai_chat_service.complete(text, user, ctx)
        except Exception as exc:
            logger.warning("AI chat fallback to rules: %s", exc)

    return _answer_with_rules(text, ctx)
