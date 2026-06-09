"""Alert model. Alerts are targeted at a specific role (or everyone)."""
from datetime import datetime

from extensions import db


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)

    # LOW | MEDIUM | HIGH | CRITICAL
    severity = db.Column(db.String(20), nullable=False, default="LOW")

    # A role name from utils.rbac.Role, or "ALL" to broadcast to everyone.
    target_role = db.Column(db.String(40), nullable=False, default="ALL")

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "severity": self.severity,
            "target_role": self.target_role,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
