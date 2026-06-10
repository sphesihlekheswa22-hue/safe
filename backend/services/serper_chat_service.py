"""Safety Assistant replies using SafeRoute DB + Serper real-time SA search."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from services import serper_service

SA_TZ = ZoneInfo("Africa/Johannesburg")

_OFF_TOPIC = re.compile(
    r"\b(recipe|cook|homework|math problem|python code|javascript|movie|song lyrics|"
    r"crypto price|stock market|weather forecast(?!\s+(alert|warning)))\b",
    re.I,
)

_SCOPE_HINT = (
    "I only answer **SafeRoute AI** questions about **South Africa** community safety — "
    "risk areas, alerts, incidents, safe routes, and live local updates. "
    "Try: \"Is Umlazi safe today?\" or \"Active alerts in Durban\"."
)


def _sa_now_str() -> str:
    return datetime.now(SA_TZ).strftime("%A %d %B %Y, %H:%M SAST")


def _level_advice(level: str) -> str:
    tips = {
        "LOW": "Conditions look calm — stay aware.",
        "MEDIUM": "Exercise caution; check alerts before travelling.",
        "HIGH": "Avoid non-essential travel; use **Safe Routes**.",
        "CRITICAL": "Avoid the area; follow official alerts.",
    }
    return tips.get(level, tips["MEDIUM"])


def _match_area(text: str, areas: list) -> dict | None:
    lower = text.lower()
    for area in areas:
        name = area["area_name"].lower()
        if name in lower or any(part in lower for part in name.split() if len(part) > 3):
            return area
    return None


def _format_db_section(message: str, ctx: dict) -> tuple[str, dict | None]:
    """Build the platform-data portion of the reply."""
    lower = message.lower()
    areas = ctx.get("risk_areas") or []
    events = ctx.get("events") or []
    alerts = ctx.get("alerts") or []
    action = None

    if re.search(r"\b(hi|hello|hey|help|what can you)\b", lower):
        return (
            "I'm your **SafeRoute Safety Assistant** for **South Africa**. "
            "I combine **live platform data** with **real-time web search** (SAST).\n\n"
            "Ask about **Umlazi**, **Durban CBD**, **UKZN**, alerts, incidents, or safe routes.",
            None,
        )

    if ctx.get("computed_route"):
        r = ctx["computed_route"]
        action = {"label": "View on map", "href": "/routes"}
        return (
            f"**{r['origin']} → {r['destination']}** (SafeRoute corridor)\n"
            f"Risk: **{r['risk_score']}/100** ({r.get('risk_level', 'SAFE')}).\n"
            f"{r.get('explanation', '')}",
            action,
        )

    if re.search(r"\b(alert|warning|broadcast)\b", lower):
        if not alerts:
            return "No **active alerts** in SafeRoute for your role right now.", {"label": "Alerts", "href": "/alerts"}
        lines = [f"• [{a['severity']}] {a['message']}" for a in alerts[:5]]
        return f"**{len(alerts)} SafeRoute alert(s):**\n\n" + "\n".join(lines), {"label": "View alerts", "href": "/alerts"}

    if re.search(r"\b(event|incident|happening|protest|unrest|crime)\b", lower):
        if events:
            lines = [f"• **{e['title']}** ({e['location']}) — severity {e['severity']}/5" for e in events[:5]]
            return "**Recent incidents (SafeRoute database):**\n\n" + "\n".join(lines), {"label": "View events", "href": "/events"}

    area = _match_area(message, areas)
    if area:
        related = [e for e in events if area["area_name"].lower() in (e.get("location") or "").lower()]
        text = (
            f"**{area['area_name']}** — SafeRoute risk **{area['risk_score']}/100** "
            f"({area['risk_level']}).\n{_level_advice(area['risk_level'])}"
        )
        if related:
            text += "\n\nNearby incidents:\n" + "\n".join(
                f"• {e['title']} (sev {e['severity']})" for e in related[:3]
            )
        return text, {"label": "Safety map", "href": "/map"}

    if areas:
        top = areas[0]
        return (
            f"City average risk: **{ctx.get('avg_risk', 0)}/100**.\n"
            f"Highest monitored area: **{top['area_name']}** ({top['risk_score']}/100, {top['risk_level']}).\n"
            f"{_level_advice(top['risk_level'])}",
            {"label": "Dashboard", "href": "/dashboard"},
        )

    return "Checking SafeRoute platform data and live South Africa sources…", None


def _format_serper_section(serper: dict) -> str:
    parts = []
    box = serper.get("answer_box")
    if isinstance(box, dict) and box.get("answer"):
        parts.append(f"**Web summary:** {box['answer']}")
    elif isinstance(box, dict) and box.get("snippet"):
        parts.append(f"**Web summary:** {box['snippet']}")

    web = serper.get("web") or []
    if web:
        parts.append("\n**Live web results (South Africa):**")
        for item in web[:3]:
            snippet = (item.get("snippet") or "").strip()
            title = item.get("title", "Source")
            if snippet:
                parts.append(f"• **{title}** — {snippet[:220]}")

    news = serper.get("news") or []
    if news:
        parts.append("\n**Latest SA news:**")
        for item in news[:3]:
            when = f" ({item['date']})" if item.get("date") else ""
            src = f" — {item['source']}" if item.get("source") else ""
            parts.append(f"• **{item['title']}**{when}{src}")

    return "\n".join(parts)


def _suggestions(message: str, ctx: dict) -> list[str]:
    area = _match_area(message, ctx.get("risk_areas") or [])
    if area:
        return ["Active alerts", "Recent incidents", "Find safe route"]
    return ["Is Umlazi safe?", "Durban news today", "Active alerts"]


def answer(message: str, user, ctx: dict) -> dict:
    text = (message or "").strip()
    if _OFF_TOPIC.search(text):
        return {"reply": _SCOPE_HINT, "suggestions": ["Is Durban safe?", "Active alerts"]}

    db_part, action = _format_db_section(text, ctx)
    serper = serper_service.fetch_sa_context(text)
    serper_part = _format_serper_section(serper)

    reply = f"**{_sa_now_str()}**\n\n{db_part}"
    if serper_part:
        reply += f"\n\n{serper_part}"
    reply += (
        "\n\n_Data: SafeRoute database + Serper live search (ZA). "
        "Always verify critical safety decisions with official SAPS / municipal sources._"
    )

    return {
        "reply": reply,
        "suggestions": _suggestions(text, ctx)[:3],
        "action": action,
    }
