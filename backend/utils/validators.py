"""Validation helpers raising a uniform ValidationError.

Kept dependency-free (no marshmallow) so the project stays lightweight. The
schema modules build on these primitives.
"""


class ValidationError(Exception):
    """Raised when request input fails validation.

    Carries an HTTP-friendly message and an optional field map.
    """

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field

    def to_dict(self):
        d = {"error": self.message}
        if self.field:
            d["field"] = self.field
        return d


def require(data: dict, *fields):
    missing = [f for f in fields if not str(data.get(f, "")).strip()]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def as_int(value, field, minimum=None, maximum=None):
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be an integer.", field)
    if minimum is not None and n < minimum:
        raise ValidationError(f"'{field}' must be >= {minimum}.", field)
    if maximum is not None and n > maximum:
        raise ValidationError(f"'{field}' must be <= {maximum}.", field)
    return n


def one_of(value, field, allowed):
    if value not in allowed:
        raise ValidationError(f"'{field}' must be one of {list(allowed)}.", field)
    return value
