"""Audit log model: records security-relevant actions for accountability."""
from datetime import datetime

from extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    actor_email = db.Column(db.String(255))
    action = db.Column(db.String(120), nullable=False)
    target = db.Column(db.String(255))
    detail = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "action": self.action,
            "target": self.target,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
