"""Recommended safe-route model."""
from datetime import datetime

from extensions import db


class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    start_location = db.Column(db.String(255), nullable=False)
    end_location = db.Column(db.String(255), nullable=False)
    start_lat = db.Column(db.Float, nullable=True)
    start_lng = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lng = db.Column(db.Float, nullable=True)
    risk_score = db.Column(db.Float, nullable=False, default=0.0)

    # GeoJSON LineString describing the route geometry, stored as JSON text.
    geojson = db.Column(db.JSON, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, *, include_geojson=True):
        data = {
            "id": self.id,
            "start_location": self.start_location,
            "end_location": self.end_location,
            "start_lat": self.start_lat,
            "start_lng": self.start_lng,
            "end_lat": self.end_lat,
            "end_lng": self.end_lng,
            "risk_score": round(self.risk_score, 2),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
        if include_geojson:
            data["geojson"] = self.geojson
        return data
