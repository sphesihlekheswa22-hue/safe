"""Institution model."""
from datetime import datetime

from extensions import db


class Institution(db.Model):
    __tablename__ = "institutions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    type = db.Column(db.String(80), nullable=False, default="GENERIC")
    location = db.Column(db.String(255))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    radius_km = db.Column(db.Float, nullable=True, default=8.0)
    staff_count = db.Column(db.Integer, nullable=True, default=0)
    student_count = db.Column(db.Integer, nullable=True, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    users = db.relationship("User", back_populates="institution", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_km": self.radius_km,
            "staff_count": self.staff_count or 0,
            "student_count": self.student_count or 0,
            "user_count": self.users.count(),
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
