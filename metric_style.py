"""Helpers for consistent positive/negative performance metric styling."""

import re


def metric_class(value):
    """Return a color class from the numeric value visible to the reader."""
    cleaned = re.sub(r"[^0-9.+-]", "", str(value))
    try:
        number = float(cleaned)
    except ValueError:
        return ""
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return ""
