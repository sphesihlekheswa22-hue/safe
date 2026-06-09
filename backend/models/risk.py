"""Risk area model: computed risk score per named area."""
from datetime import datetime

from extensions import db


class RiskArea(db.Model):
    __tablename__ = "risk_areas"

    id = db.Column(db.Integer, primary_key=True)
    area_name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    risk_score = db.Column(db.Float, nullable=False, default=0.0)
    sentiment_score = db.Column(db.Float, nullable=False, default=0.0)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    radius_km = db.Column(db.Float, nullable=True, default=2.5)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @property
    def risk_level(self) -> str:
        if self.risk_score >= 85:
            return "CRITICAL"
        if self.risk_score >= 70:
            return "HIGH"
        if self.risk_score >= 40:
            return "MEDIUM"
        return "LOW"

    def to_dict(self):
        return {
            "id": self.id,
            "area_name": self.area_name,
            "risk_score": round(self.risk_score, 2),
            "sentiment_score": round(self.sentiment_score, 2),
            "risk_level": self.risk_level,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_km": self.radius_km,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }
