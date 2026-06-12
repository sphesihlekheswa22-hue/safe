"""Safety Assistant — DB context + Serper real-time SA search + optional LLM."""
from __future__ import annotations

import logging
import re

from models.event import Event
from models.risk import RiskArea
from models.route import Route
from services import route_optimizer
from services import ai_chat_service
from services import serper_service
from services import serper_chat_service

logger = logging.getLogger(__name__)


def _gather_context(user) -> dict:
    risk_areas = RiskArea.query.order_by(RiskArea.risk_score.desc()).all()
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(12).all()
    routes = Route.query.order_by(Route.risk_score.asc()).limit(6).all()

    avg_risk = (
        round(sum(a.risk_score for a in risk_areas) / len(risk_areas), 1)
        if risk_areas
        else 0.0
    )

    return {
        "risk_areas": [a.to_dict() for a in risk_areas],
        "events": [e.to_dict() for e in recent_events],
        "routes": [r.to_dict() for r in routes],
        "avg_risk": avg_risk,
        "computed_route": None,
    }


def _maybe_compute_route(message: str, ctx: dict) -> None:
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
    return serper_chat_service.answer(message, None, ctx)


def answer(message: str, user) -> dict:
    text = (message or "").strip()
    if not text:
        return {"reply": "Ask me about area safety, incidents, or safe routes in South Africa."}

    ctx = _gather_context(user)
    _maybe_compute_route(text, ctx)

    if serper_service.is_enabled():
        try:
            return serper_chat_service.answer(text, user, ctx)
        except Exception as exc:
            logger.warning("Serper chat error, trying fallback: %s", exc)

    if ai_chat_service.is_enabled():
        try:
            ctx["serper"] = {}
            return ai_chat_service.complete(text, user, ctx)
        except Exception as exc:
            logger.warning("LLM chat fallback: %s", exc)

    return _answer_with_rules(text, ctx)
