"""Shared parsers for the Unleashed exports.

Dates are DD/MM/YYYY; money/quantity fields carry thousands separators and may
be blank. All parsers fail soft (return None / 0.0) so a single malformed cell
never aborts a load.
"""
from datetime import date, datetime
from typing import Optional

_DATE_FMT = "%d/%m/%Y"


def parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, _DATE_FMT).date()
    except ValueError:
        return None


def days_between(earlier: Optional[date], anchor: date) -> Optional[int]:
    """Whole days from `earlier` up to `anchor` (recency)."""
    if earlier is None:
        return None
    return (anchor - earlier).days


def parse_money(value: str) -> float:
    """Parse a currency cell like '1,076.44' -> 1076.44; blanks -> 0.0."""
    value = (value or "").strip().replace(",", "")
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


# Quantities/stock use the same forgiving numeric parse.
parse_number = parse_money
