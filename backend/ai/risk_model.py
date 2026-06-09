"""Risk model wrapper around the weighted risk engine."""
from services import risk_engine


class RiskModel:
    name = "weighted-linear-v1"
    weights = {
        "severity": risk_engine.W_SEVERITY,
        "density": risk_engine.W_DENSITY,
        "sentiment": risk_engine.W_SENTIMENT,
    }

    def predict(self, events, sentiment_score: float) -> float:
        return risk_engine.compute_risk(events, sentiment_score)


_model = RiskModel()


def get_model() -> RiskModel:
    return _model
