"""Safety Assistant replies using SafeRoute DB + Serper real-time SA search."""

from __future__ import annotations



import re

from datetime import datetime

from zoneinfo import ZoneInfo



from services import gazetteer

from services import serper_service



SA_TZ = ZoneInfo("Africa/Johannesburg")



_OFF_TOPIC = re.compile(

    r"\b(recipe|cook|homework|math problem|python code|javascript|movie|song lyrics|"

    r"crypto price|stock market|celebrity|biography|net worth|dating|football score|"

    r"who is|who was|tell me about|what do you know about|information about|bio of|"

    r"age of|born in|president of|prime minister)\b",

    re.I,

)



_SAFETY_KEYWORDS = re.compile(

    r"\b(safe|safety|risk|alert|warn|incident|event|route|routes|travel|navigat|"

    r"crime|protest|unrest|danger|dangerous|avoid|secure|corridor|area|zone|"

    r"saferoute|happening|shooting|robbery|hijack|stab|fire|flood|emergency|"

    r"saps|police|hospital|campus|taxi|transit|metro|unrest|hotspot|evacuat|"

    r"severity|broadcast|dashboard|analytics|institution|transport|government)\b",

    re.I,

)



_SA_GEO = re.compile(

    r"\b(south africa|durban|umlazi|ukzn|johannesburg|joburg|soweto|"

    r"cape town|kzn|kwazulu|ethekwini|pinetown|umhlanga|chatsworth|"

    r"phoenix|warwick|sandton|alexandra|mitchells plain|khayelitsha|bellville)\b",

    re.I,

)



# Bare person-name style queries (e.g. "Thabo Mbeki" or "John Smith?")

_BARE_NAME = re.compile(

    r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s*\??$",

)



_SCOPE_HINT = (

    "I can only help with **SafeRoute AI** and **South Africa community safety** — "

    "risk areas, alerts, incidents, safe routes, and live local safety updates.\n\n"

    "I can't look up people or general knowledge. Try:\n"

    "• \"Is **Soshanguve** safe today?\"\n"

    "• \"**Recent incidents** in Pretoria CBD\"\n"

    "• \"**Safe route** from Pretoria Station to Hatfield\""

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





def _mentions_gazetteer(text: str) -> bool:

    lower = text.lower()

    return any(place in lower for place in gazetteer.GAZETTEER)





def _mentions_platform_event(text: str, events: list) -> bool:

    lower = text.lower()

    for ev in events:

        loc = (ev.get("location") or "").lower()

        if loc and len(loc) > 3 and loc in lower:

            return True

    return False





def is_in_scope(message: str, ctx: dict) -> bool:

    """Return True only for SafeRoute / SA safety questions."""

    text = (message or "").strip()

    if not text or len(text) > 500:

        return False



    lower = text.lower()



    if _OFF_TOPIC.search(lower):

        return False



    if _BARE_NAME.match(text) and not _SAFETY_KEYWORDS.search(lower):

        return False



    # Short vague queries without safety intent (e.g. random names or topics)

    words = re.findall(r"[a-zA-Z']+", text)

    if len(words) <= 4 and not _SAFETY_KEYWORDS.search(lower) and not _SA_GEO.search(lower):

        if not _match_area(text, ctx.get("risk_areas") or []):

            if not _mentions_gazetteer(text):

                if not re.search(r"\b(hi|hello|hey|help|what can you)\b", lower):

                    return False



    if re.search(r"\b(hi|hello|hey|help|what can you)\b", lower):

        return True

    if ctx.get("computed_route"):

        return True

    if _SAFETY_KEYWORDS.search(lower):

        return True

    if _SA_GEO.search(lower):

        return True

    if _match_area(text, ctx.get("risk_areas") or []):

        return True

    if _mentions_gazetteer(text):

        return True

    if _mentions_platform_event(text, ctx.get("events") or []):

        return True



    return False





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

            "Ask about **Soshanguve**, **Pretoria CBD**, **Hatfield**, incidents, or safe routes.",

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
        if not events:
            return "No **recent incidents** in SafeRoute right now.", {"label": "Events", "href": "/events"}
        lines = [f"• **{e['title']}** ({e['location']}) — severity {e['severity']}/5" for e in events[:5]]
        return f"**{len(events)} recent incident(s):**\n\n" + "\n".join(lines), {"label": "View events", "href": "/events"}



    if re.search(r"\b(event|incident|happening|protest|unrest|crime)\b", lower):

        if events:

            lines = [f"• **{e['title']}** ({e['location']}) — severity {e['severity']}/5" for e in events[:5]]

            return "**Recent incidents (SafeRoute database):**\n\n" + "\n".join(lines), {"label": "View events", "href": "/events"}

        return "No matching incidents in SafeRoute right now.", {"label": "View events", "href": "/events"}



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



    if re.search(r"\b(safe|safety|risk|dangerous|safest)\b", lower) and areas:

        top = areas[0]

        return (

            f"City average risk: **{ctx.get('avg_risk', 0)}/100**.\n"

            f"Highest monitored area: **{top['area_name']}** ({top['risk_score']}/100, {top['risk_level']}).\n"

            f"{_level_advice(top['risk_level'])}",

            {"label": "Dashboard", "href": "/dashboard"},

        )



    return "Here is what SafeRoute shows for your question:", None





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

    return ["Is Soshanguve safe?", "Pretoria safety today", "Recent incidents"]





def _refuse() -> dict:

    return {

        "reply": _SCOPE_HINT,

        "suggestions": ["Is Soshanguve safe?", "Recent incidents", "Route to Hatfield"],

    }





def answer(message: str, user, ctx: dict) -> dict:

    text = (message or "").strip()



    if not is_in_scope(text, ctx):

        return _refuse()



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


