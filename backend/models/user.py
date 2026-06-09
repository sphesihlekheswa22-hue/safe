"""User model with role-based access control fields."""
from datetime import datetime

from extensions import db
from utils.rbac import Role


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Role is server-controlled only. Default for self-registration.
    role = db.Column(db.String(40), nullable=False, default=Role.PUBLIC_USER)

    institution_id = db.Column(
        db.Integer, db.ForeignKey("institutions.id"), nullable=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    institution = db.relationship("Institution", back_populates="users")

    def to_dict(self, include_institution=False):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "institution_id": self.institution_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
        if include_institution and self.institution is not None:
            data["institution"] = {
                "id": self.institution.id,
                "name": self.institution.name,
            }
        return data
