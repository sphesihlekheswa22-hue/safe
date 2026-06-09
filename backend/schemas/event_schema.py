"""Validation for event payloads."""
from utils.validators import ValidationError, require, as_int
from utils.security import clean_str
from utils.constants import MIN_SEVERITY, MAX_SEVERITY


def validate_create(data: dict) -> dict:
    require(data, "title", "location")
    title = clean_str(data.get("title"), 200)
    location = clean_str(data.get("location"), 255)
    if not title:
        raise ValidationError("Title is required.", "title")
    if not location:
        raise ValidationError("Location is required.", "location")
    severity = as_int(data.get("severity", 1), "severity", MIN_SEVERITY, MAX_SEVERITY)
    return {
        "title": title,
        "location": location,
        "description": clean_str(data.get("description"), 2000),
        "severity": severity,
        "source": clean_str(data.get("source"), 120) or "manual",
    }


def validate_update(data: dict) -> dict:
    out = {}
    if "title" in data:
        title = clean_str(data.get("title"), 200)
        if not title:
            raise ValidationError("Title cannot be empty.", "title")
        out["title"] = title
    if "location" in data:
        location = clean_str(data.get("location"), 255)
        if not location:
            raise ValidationError("Location cannot be empty.", "location")
        out["location"] = location
    if "description" in data:
        out["description"] = clean_str(data.get("description"), 2000)
    if "severity" in data:
        out["severity"] = as_int(
            data.get("severity"), "severity", MIN_SEVERITY, MAX_SEVERITY
        )
    if "source" in data:
        out["source"] = clean_str(data.get("source"), 120)
    return out
