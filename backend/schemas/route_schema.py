"""Validation for route generation payloads."""
from utils.validators import ValidationError, require
from utils.security import clean_str


def _optional_float(data: dict, key: str):
    val = data.get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be a number.") from exc


def validate_generate(data: dict) -> dict:
    start = clean_str(data.get("start_location"), 255)
    end = clean_str(data.get("end_location"), 255)
    start_lat = _optional_float(data, "start_lat")
    start_lng = _optional_float(data, "start_lng")
    end_lat = _optional_float(data, "end_lat")
    end_lng = _optional_float(data, "end_lng")

    has_start_coords = start_lat is not None and start_lng is not None
    has_end_coords = end_lat is not None and end_lng is not None

    if not has_start_coords and not start:
        raise ValidationError("Provide an origin name or use your current location.")
    if not has_end_coords and not end:
        raise ValidationError("Provide a destination name or address.")

    return {
        "start_location": start or "",
        "end_location": end or "",
        "start_lat": start_lat,
        "start_lng": start_lng,
        "end_lat": end_lat,
        "end_lng": end_lng,
    }
