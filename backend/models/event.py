"""Community event / risk signal model."""
from datetime import datetime

from extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # 1 (minor) .. 5 (critical)
    severity = db.Column(db.Integer, nullable=False, default=1)
    source = db.Column(db.String(120), default="manual")

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "severity": self.severity,
            "source": self.source,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
