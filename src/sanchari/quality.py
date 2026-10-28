"""Small pure-Python checks, reused and expanded in later pipeline stages."""
from collections.abc import Mapping


def require_fields(record: Mapping[str, object], fields: tuple[str, ...]) -> bool:
    """Return True if all fields exist and are not None or empty strings."""
    return all(field in record and record[field] is not None and record[field] != "" for field in fields)


def is_nonnegative_number(value: object) -> bool:
    """Strictly accept nonnegative numeric types, not booleans or numeric strings."""
    from math import isfinite

    return type(value) in (int, float) and isfinite(value) and value >= 0
