"""Validation for alert payloads."""
from utils.validators import ValidationError, require, one_of
from utils.security import clean_str
from utils.constants import ALERT_SEVERITIES
from utils.rbac import Role


def validate_create(data: dict) -> dict:
    require(data, "message")
    message = clean_str(data.get("message"), 1000)
    if not message:
        raise ValidationError("Alert message is required.", "message")
    severity = (data.get("severity") or "LOW").upper()
    one_of(severity, "severity", ALERT_SEVERITIES)
    target_role = (data.get("target_role") or "ALL").upper()
    if target_role != "ALL" and not Role.is_valid(target_role):
        raise ValidationError("target_role must be 'ALL' or a valid role.", "target_role")
    return {"message": message, "severity": severity, "target_role": target_role}
