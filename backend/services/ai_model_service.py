"""Facade over the AI models used by the API layer."""
from ai.sentiment_model import get_model as get_sentiment_model
from ai.risk_model import get_model as get_risk_model
from ai import embeddings


def model_info() -> dict:
    sm = get_sentiment_model()
    rm = get_risk_model()
    return {
        "sentiment_model": {"name": sm.name},
        "risk_model": {"name": rm.name, "weights": rm.weights},
        "embeddings": {"dim": embeddings.DIM, "type": "hashing-stub"},
    }


def analyze_text(text: str) -> dict:
    sm = get_sentiment_model()
    return {
        "sentiment": round(sm.predict(text), 3),
        "embedding_preview": embeddings.embed(text)[:8],
    }
