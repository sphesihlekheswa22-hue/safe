"""Sentiment model wrapper.

Wraps the lexicon-based sentiment scorer behind a model-like interface so a
heavier ML model could be swapped in later without touching callers.
"""
from services import sentiment_service


class SentimentModel:
    name = "lexicon-v1"

    def predict(self, text: str) -> float:
        """Return sentiment in [-1, 1]."""
        return sentiment_service.analyze(text)

    def predict_batch(self, texts) -> float:
        return sentiment_service.analyze_many(texts)


_model = SentimentModel()


def get_model() -> SentimentModel:
    return _model
