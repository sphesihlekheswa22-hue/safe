"""Subscription model: a user subscribing to alerts for a given area/role.

Used by the notification service to decide who should receive an alert.
"""
from datetime import datetime

from extensions import db


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    area_name = db.Column(db.String(255), nullable=True)  # None => all areas
    channel = db.Column(db.String(40), nullable=False, default="in_app")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "area_name": self.area_name,
            "channel": self.channel,
            "active": self.active,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
