"""A customer's ordering rhythm — the usual gap between their orders.

Lives on its own because two layers need it and they sit on opposite sides of
the import graph: `utils/attention.py` ranks the queue with it (and imports
`utils/recommend.py` to do so), while `utils/profile.py` needs it to decide
whether a "gone quiet" relationship flag is still true. Profile can't import
attention without a cycle, so the arithmetic lives here and both import it.

The rhythm is the AVERAGE gap between distinct order dates, not the median:
accounts often place a burst of orders in one week, which would drag a median
down to a few days and flag them as late almost immediately.
"""
from typing import Optional

from constants.attention import (
    MIN_OVERDUE_DAYS,
    MIN_RHYTHM_ORDER_DATES,
    OVERDUE_RATIO,
)


def rhythm_days(order_dates) -> Optional[int]:
    """Average days between distinct order dates; None with too few orders."""
    if len(order_dates) < MIN_RHYTHM_ORDER_DATES:
        return None
    return max(1, round((order_dates[-1] - order_dates[0]).days / (len(order_dates) - 1)))


def is_overdue(rhythm: Optional[int], days_since: Optional[int]) -> bool:
    if rhythm is None or days_since is None:
        return False
    return days_since >= rhythm * OVERDUE_RATIO and days_since - rhythm >= MIN_OVERDUE_DAYS


def within_rhythm(rhythm: Optional[int], days_since: Optional[int]) -> bool:
    """They have ordered inside their usual gap — still buying on schedule.

    Deliberately stricter than "not overdue": `is_overdue` allows a grace period
    on top of the rhythm, so a customer can be drifting late without tripping it.
    A claim that a customer has gone quiet should only be overturned when they
    are demonstrably still on schedule, not merely not-yet-late.
    """
    if rhythm is None or days_since is None:
        return False
    return days_since <= rhythm
