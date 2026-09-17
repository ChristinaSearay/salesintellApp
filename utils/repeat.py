"""A customer's buying rhythm: what they repurchase, how often, and what is due.

Works off `CustomerProfile.purchases` (noise already excluded), so a "cadence"
is a real product code or product group bought on several separate dates. The
usual interval is the MEDIAN gap between consecutive order dates — a median
shrugs off the one-off bulk order that would drag a mean around.

Nothing here decides what to pitch; utils/candidates.py turns these into cards.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Callable, Dict, List, Optional, Tuple

from constants.repeat import (
    LAPSED_RATIO,
    MIN_GROUP_PURCHASE_DATES,
    MIN_ITEM_PURCHASE_DATES,
    WEEKS_PHRASE_MAX_DAYS,
)


@dataclass(frozen=True)
class Cadence:
    """One thing a customer buys repeatedly — a product code or a group."""
    key: str                    # product code, or group name
    description: str
    group: str
    dates: Tuple[date, ...]     # distinct order dates, oldest first
    quantity: float             # total units over the window
    value: float                # total spend over the window
    last_quantity: float        # units on the most recent order

    @property
    def times_bought(self) -> int:
        return len(self.dates)

    @property
    def last_bought(self) -> date:
        return self.dates[-1]

    @property
    def interval_days(self) -> Optional[int]:
        """Median gap between consecutive order dates; None if never repeated."""
        gaps = [(b - a).days for a, b in zip(self.dates, self.dates[1:]) if (b - a).days > 0]
        return int(median(gaps)) if gaps else None

    def days_since(self, anchor: date) -> int:
        return (anchor - self.last_bought).days

    def due_ratio(self, anchor: date) -> Optional[float]:
        interval = self.interval_days
        return None if not interval else self.days_since(anchor) / interval

    def is_due(self, anchor: date, ratio: float) -> bool:
        due = self.due_ratio(anchor)
        return due is not None and due >= ratio

    def is_lapsed(self, anchor: date) -> bool:
        return self.is_due(anchor, LAPSED_RATIO)

    @property
    def interval_phrase(self) -> str:
        """'about every 6 weeks' — only meaningful with a few orders behind it."""
        unit = unit_phrase(self.interval_days)
        return f"about every {unit}" if unit else ""

    @property
    def gap_phrase(self) -> str:
        """'about 5 months apart' — honest wording when there is only one gap."""
        unit = unit_phrase(self.interval_days)
        return f"about {unit} apart" if unit else ""


def unit_phrase(days: Optional[int]) -> str:
    """'6 weeks' / '4 months' — rep-readable, never in raw days."""
    if not days:
        return ""
    if days <= WEEKS_PHRASE_MAX_DAYS:
        weeks = max(1, round(days / 7))
        return f"{weeks} week{'s' if weeks > 1 else ''}"
    months = max(1, round(days / 30))
    return f"{months} month{'s' if months > 1 else ''}"


def _cadences(purchases, key: Callable, describe: Callable, min_dates: int) -> List[Cadence]:
    buckets: Dict[str, list] = defaultdict(list)
    for p in purchases:
        buckets[key(p)].append(p)

    out = []
    for k, items in buckets.items():
        dates = tuple(sorted({p.when for p in items}))
        if len(dates) < min_dates:
            continue
        last = dates[-1]
        out.append(Cadence(
            key=k,
            description=describe(items),
            group=items[0].group,
            dates=dates,
            quantity=sum(p.quantity for p in items),
            value=sum(p.value for p in items),
            last_quantity=sum(p.quantity for p in items if p.when == last),
        ))
    return sorted(out, key=lambda c: (-c.value, c.key))


def item_cadences(purchases, min_dates: int = MIN_ITEM_PURCHASE_DATES) -> List[Cadence]:
    """Per product code, biggest spend first."""
    return _cadences(
        purchases,
        key=lambda p: p.code,
        # The description can vary between orders; the latest one wins.
        describe=lambda items: max(items, key=lambda p: p.when).description,
        min_dates=min_dates,
    )


def group_cadences(purchases, min_dates: int = MIN_GROUP_PURCHASE_DATES) -> List[Cadence]:
    """Per product group, biggest spend first."""
    return _cadences(
        purchases,
        key=lambda p: p.group,
        describe=lambda items: items[0].group,
        min_dates=min_dates,
    )


def due(cadences: List[Cadence], anchor: date, ratio: float) -> List[Cadence]:
    """Those overdue by `ratio`× their usual interval: the ones simply due first
    (they are the easy ask), then long-lapsed ones, biggest spend first within
    each."""
    return sorted((c for c in cadences if c.is_due(anchor, ratio)),
                  key=lambda c: (c.is_lapsed(anchor), -c.value))
