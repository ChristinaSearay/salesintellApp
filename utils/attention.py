"""The "needs attention" queue: which customers a rep should work on next.

Tiers, in order (constants/attention.py):
  1. OVERDUE         late against their own ordering rhythm
  2. NO_RECENT_NOTE  everyone else without a note in the snooze window
  3. RECENTLY_NOTED  noted within the window — the back of the line, oldest note first
Biggest 2-year spend first within tiers 1 and 2. Saving a note (or confirming a
WhatsApp update) moves a customer to tier 3, so the next one pops up.

A customer's rhythm is the AVERAGE gap between their distinct order dates, not
the median: accounts often place a burst of orders in one week, which would
drag a median down to a few days and flag them as late almost immediately.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from constants.attention import (
    ATTENTION_QUEUE_SIZE,
    MIN_OVERDUE_DAYS,
    MIN_RHYTHM_ORDER_DATES,
    NOTE_SNOOZE_DAYS,
    OVERDUE_RATIO,
    TIER_ORDER,
    AttentionReason,
)
from utils.intel import IntelUpdate, latest_updates
from utils.recommend import account_card, all_profiles
from utils.repeat import unit_phrase


@dataclass(frozen=True)
class Attention:
    code: str
    name: str
    spend: float
    reason: AttentionReason
    rhythm_days: Optional[int]      # usual gap between orders; None without a rhythm
    days_since_order: Optional[int]
    note: Optional[IntelUpdate]
    note_days: Optional[int]        # days since the newest note

    def sort_key(self):
        if self.reason is AttentionReason.RECENTLY_NOTED:
            return (TIER_ORDER[self.reason], self.note.ts)
        return (TIER_ORDER[self.reason], -self.spend, self.name)


def rhythm_days(order_dates) -> Optional[int]:
    """Average days between distinct order dates; None with too few orders."""
    if len(order_dates) < MIN_RHYTHM_ORDER_DATES:
        return None
    return max(1, round((order_dates[-1] - order_dates[0]).days / (len(order_dates) - 1)))


def is_overdue(rhythm: Optional[int], days_since: Optional[int]) -> bool:
    if rhythm is None or days_since is None:
        return False
    return days_since >= rhythm * OVERDUE_RATIO and days_since - rhythm >= MIN_OVERDUE_DAYS


def _days_since(iso_ts: str, now: datetime) -> Optional[int]:
    try:
        when = datetime.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0, (now - when).days)


def _assess(profile, note: Optional[IntelUpdate], now: datetime) -> Attention:
    rhythm = rhythm_days(profile.order_dates)
    note_days = _days_since(note.ts, now) if note else None
    if note_days is not None and note_days < NOTE_SNOOZE_DAYS:
        reason = AttentionReason.RECENTLY_NOTED
    elif is_overdue(rhythm, profile.recency_days):
        reason = AttentionReason.OVERDUE
    else:
        reason = AttentionReason.NO_RECENT_NOTE
    return Attention(
        code=profile.customer.code,
        name=profile.customer.name,
        spend=profile.monetary,
        reason=reason,
        rhythm_days=rhythm,
        days_since_order=profile.recency_days,
        note=note,
        note_days=note_days,
    )


def _days(n: int) -> str:
    return "today" if n == 0 else "yesterday" if n == 1 else f"{n} days ago"


def _why(a: Attention) -> str:
    """One plain-English line: why this customer is in the queue (the card's
    meta line already shows spend and last order)."""
    if a.reason is AttentionReason.OVERDUE:
        late = a.days_since_order - a.rhythm_days
        return f"Usually orders every {unit_phrase(a.rhythm_days)} — now {unit_phrase(late)} late"
    if a.reason is AttentionReason.RECENTLY_NOTED:
        return f"Noted {_days(a.note_days)}"
    if a.note_days is not None:
        return f"No note for {a.note_days} days"
    return "No notes yet"


def ranked() -> List[Attention]:
    """Every active customer, in queue order."""
    now = datetime.now(timezone.utc)
    notes = latest_updates()
    profiles = all_profiles()
    return sorted((_assess(p, notes.get(code), now) for code, p in profiles.items()),
                  key=Attention.sort_key)


def attention_payload(n: int = ATTENTION_QUEUE_SIZE) -> dict:
    everyone = ranked()
    queue = []
    for a in everyone[:n]:
        card = account_card(a.code)
        card.update(
            reason=a.reason.value,
            why=_why(a),
            rhythm_days=a.rhythm_days,
            last_note=({"text": " ".join(a.note.hooks), "ts": a.note.ts,
                        "source": a.note.source, "days_ago": a.note_days}
                       if a.note else None),
        )
        queue.append(card)
    return {
        "queue": queue,
        "overdue": sum(1 for a in everyone if a.reason is AttentionReason.OVERDUE),
        "noted_recently": sum(1 for a in everyone if a.reason is AttentionReason.RECENTLY_NOTED),
        "snooze_days": NOTE_SNOOZE_DAYS,
    }
