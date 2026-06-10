"""Serper.dev — real-time Google search/news for South Africa safety context."""
from __future__ import annotations

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

SERPER_BASE = "https://google.serper.dev"


def is_enabled() -> bool:
    return bool(os.environ.get("SERPER_API_KEY", "").strip())


def _headers() -> dict:
    return {
        "X-API-KEY": os.environ["SERPER_API_KEY"].strip(),
        "Content-Type": "application/json",
    }


def _sa_query(query: str) -> str:
    """Bias searches toward South Africa safety topics."""
    q = (query or "").strip()
    if not q:
        return "South Africa community safety news"
    lower = q.lower()
    if "south africa" not in lower and " durban" not in lower and "kzn" not in lower:
        q = f"{q} South Africa"
    return q


def _post(path: str, payload: dict) -> dict:
    resp = requests.post(
        f"{SERPER_BASE}{path}",
        headers=_headers(),
        json=payload,
        timeout=int(os.environ.get("SERPER_TIMEOUT_SEC", "20")),
    )
    if not resp.ok:
        logger.warning("Serper %s failed: %s %s", path, resp.status_code, resp.text[:200])
        raise RuntimeError(f"Search service error ({resp.status_code})")
    return resp.json()


def web_search(query: str, num: int = 5) -> dict:
    return _post("/search", {
        "q": _sa_query(query),
        "gl": "za",
        "hl": "en",
        "num": num,
    })


def news_search(query: str, num: int = 5) -> dict:
    return _post("/news", {
        "q": _sa_query(query),
        "gl": "za",
        "hl": "en",
        "num": num,
    })


def _wants_news(message: str) -> bool:
    return bool(re.search(
        r"\b(news|today|latest|happening|now|current|recent|breaking|live)\b",
        message.lower(),
    ))


def fetch_sa_context(message: str) -> dict:
    """Return trimmed web + optional news results for the assistant."""
    if not is_enabled():
        return {"web": [], "news": [], "answer_box": None}

    web = web_search(message, num=5)
    organic = [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        }
        for item in (web.get("organic") or [])[:5]
        if item.get("title")
    ]
    answer_box = web.get("answerBox") or web.get("knowledgeGraph")

    news_items = []
    if _wants_news(message) or not organic:
        try:
            news = news_search(message, num=4)
            news_items = [
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "link": item.get("link", ""),
                }
                for item in (news.get("news") or [])[:4]
                if item.get("title")
            ]
        except Exception as exc:
            logger.info("Serper news skipped: %s", exc)

    return {"web": organic, "news": news_items, "answer_box": answer_box}
