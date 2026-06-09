"""System setting model: a typed key-value store for platform configuration.

Used by the System Admin control center to manage the AI engine, security
parameters, and feature toggles without code changes. Values are stored as JSON
text so booleans / numbers / strings round-trip cleanly.
"""
import json
from datetime import datetime

from extensions import db


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), nullable=False, unique=True, index=True)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def get_value(self):
        try:
            return json.loads(self.value)
        except (TypeError, ValueError):
            return self.value

    def set_value(self, val):
        self.value = json.dumps(val)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.get_value(),
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }
