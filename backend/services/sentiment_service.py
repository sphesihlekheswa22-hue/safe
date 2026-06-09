"""Lightweight lexicon-based sentiment analysis.

No external ML dependency. Returns a score in the range [-1.0, 1.0] where
negative values indicate negative/unsafe sentiment. The risk engine converts
this into a 0..100 contribution.
"""

NEGATIVE_WORDS = {
    "danger", "dangerous", "unsafe", "crime", "violence", "violent", "attack",
    "accident", "crash", "fire", "flood", "riot", "protest", "shooting",
    "robbery", "theft", "assault", "emergency", "hazard", "warning", "death",
    "injured", "injury", "blocked", "closed", "collapse", "storm", "outage",
    "panic", "fear", "threat", "evacuate", "evacuation", "damage", "explosion",
}

POSITIVE_WORDS = {
    "safe", "secure", "calm", "clear", "open", "resolved", "restored",
    "improved", "peaceful", "stable", "normal", "reopened", "operational",
    "smooth", "reliable", "protected", "recovered", "controlled",
}


def analyze(text: str) -> float:
    """Return a sentiment score in [-1.0, 1.0] for the given text."""
    if not text:
        return 0.0

    tokens = [t.strip(".,!?;:()[]\"'").lower() for t in text.split()]
    if not tokens:
        return 0.0

    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)

    signal = pos - neg
    total = pos + neg
    if total == 0:
        return 0.0

    score = signal / total
    return max(-1.0, min(1.0, score))


def analyze_many(texts) -> float:
    """Average sentiment across multiple texts."""
    scores = [analyze(t) for t in texts if t]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
