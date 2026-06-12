"""OpenAI-powered Safety Assistant grounded in live SafeRoute database context."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

SA_TZ = ZoneInfo("Africa/Johannesburg")

SYSTEM_PROMPT = """You are the SafeRoute AI Safety Assistant for South Africa (Gauteng / Pretoria focus).

SCOPE — you MUST follow these rules:
1. ONLY answer questions about community safety, risk areas, incidents, alerts, safe routes, and how to use the SafeRoute AI platform.
2. Use ONLY facts from the LIVE_CONTEXT JSON below (platform DB + optional Serper search). Never invent incidents, alerts, risk scores, or locations.
3. All times are South Africa Standard Time (SAST, Africa/Johannesburg). Refer to "right now" using context_as_of.
4. If data is missing, say so honestly and suggest checking the Safety Map or Events pages.
5. For off-topic questions (recipes, homework, coding, politics unrelated to safety, other countries, etc.), politely refuse and redirect to safety topics.
6. Keep answers concise (under 180 words), practical, and citizen-focused. Use **bold** for area names and risk scores.
7. Prioritize CRITICAL/HIGH alerts and HIGH/CRITICAL risk areas when relevant.
8. Tailor alert visibility to the user's role shown in context.

Respond with valid JSON only (no markdown fences):
{
  "reply": "your answer in plain text with **bold** markers",
  "suggestions": ["short follow-up 1", "short follow-up 2"],
  "action": {"label": "Button label", "href": "/path"} or null
}

Valid action href values: /map, /routes, /events, /dashboard, /institution, /transport, /government
Suggestions: 0–3 short chips (max 28 chars each). action is optional."""


def is_enabled() -> bool:
    if os.environ.get("CHAT_AI_ENABLED", "true").lower() in ("0", "false", "no"):
        return False
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _sa_now() -> datetime:
    return datetime.now(SA_TZ)


def build_live_context(ctx: dict, user) -> dict:
    """Package DB context for the model."""
    now = _sa_now()
    profile = {
        "name": user.name,
        "role": user.role,
        "institution": None,
    }
    if user.institution is not None:
        profile["institution"] = {
            "name": user.institution.name,
            "location": user.institution.location,
            "type": user.institution.type,
        }

    return {
        "context_as_of": now.strftime("%A %d %B %Y, %H:%M SAST"),
        "timezone": "Africa/Johannesburg",
        "region_focus": "South Africa — Gauteng (Pretoria / Tshwane), City of Tshwane metro",
        "user": profile,
        "city_average_risk": ctx.get("avg_risk"),
        "risk_areas": ctx.get("risk_areas", []),
        "recent_incidents": ctx.get("events", []),
        "recent_events": ctx.get("events", []),
        "saved_safe_routes": ctx.get("routes", []),
        "computed_route": ctx.get("computed_route"),
        "serper_search": ctx.get("serper") or {},
    }


def _parse_ai_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict) or "reply" not in data:
        raise ValueError("AI response missing reply field")
    return {
        "reply": str(data["reply"]),
        "suggestions": data.get("suggestions") or [],
        "action": data.get("action"),
    }


def complete(message: str, user, ctx: dict) -> dict:
    """Call OpenAI Chat Completions with grounded SA safety context."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    live = build_live_context(ctx, user)

    payload = {
        "model": model,
        "temperature": 0.35,
        "max_tokens": 650,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"LIVE_CONTEXT:\n{json.dumps(live, default=str)}\n\n"
                    f"USER_QUESTION:\n{message}"
                ),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter.ai" in base:
        headers["HTTP-Referer"] = os.environ.get(
            "OPENROUTER_SITE_URL", "https://saferoute-ai-eox1.onrender.com"
        )
        headers["X-Title"] = os.environ.get("OPENROUTER_APP_NAME", "SafeRoute AI")

    resp = requests.post(
        f"{base}/chat/completions",
        headers=headers,
        json=payload,
        timeout=int(os.environ.get("OPENAI_TIMEOUT_SEC", "45")),
    )
    if not resp.ok:
        logger.warning("OpenAI chat failed: %s %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"AI service error ({resp.status_code})")

    body = resp.json()
    content = body["choices"][0]["message"]["content"]
    result = _parse_ai_json(content)

    suggestions = [s for s in result.get("suggestions", []) if isinstance(s, str)][:3]
    action = result.get("action")
    if action and (not isinstance(action, dict) or not action.get("href")):
        action = None

    return {
        "reply": result["reply"],
        "suggestions": suggestions,
        "action": action,
    }
