"""The "needs attention" queue: which customers a rep should work on next.

Tiers, in order (constants/attention.py):
  1. OVERDUE         late against their own ordering rhythm
  2. NO_RECENT_NOTE  everyone else without a note in the snooze window
  3. RECENTLY_NOTED  noted within the window — the back of the line, oldest note first
  4. MUTED           "do not alert again" — off the queue until they order (utils/mute.py)
Biggest 2-year spend first within tiers 1 and 2. Saving a note (or confirming a
WhatsApp update) moves a customer to tier 3, so the next one pops up.

A customer's rhythm (`utils/rhythm.py`) is the AVERAGE gap between their
distinct order dates, not the median: accounts often place a burst of orders in
one week, which would drag a median down to a few days and flag them as late
almost immediately.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from constants.attention import (
    ATTENTION_QUEUE_SIZE,
    NOTE_SNOOZE_DAYS,
    TIER_ORDER,
    AttentionReason,
)
from utils import mute as mutes
from utils.intel import IntelUpdate, latest_updates
from utils.recommend import account_card, all_profiles
from utils.repeat import unit_phrase
from utils.rhythm import is_overdue, rhythm_days


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


def _days_since(iso_ts: str, now: datetime) -> Optional[int]:
    try:
        when = datetime.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0, (now - when).days)


def last_order(profile) -> Optional[date]:
    return profile.order_dates[-1] if profile.order_dates else None


def _assess(profile, note: Optional[IntelUpdate], muted: bool, now: datetime) -> Attention:
    rhythm = rhythm_days(profile.order_dates)
    note_days = _days_since(note.ts, now) if note else None
    if muted:
        reason = AttentionReason.MUTED
    elif note_days is not None and note_days < NOTE_SNOOZE_DAYS:
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
    if a.reason is AttentionReason.MUTED:
        return "Muted — no reminders until they order again"
    if a.reason is AttentionReason.RECENTLY_NOTED:
        return f"Noted {_days(a.note_days)}"
    if a.note_days is not None:
        return f"No note for {a.note_days} days"
    return "No notes yet"


def _muted_codes(profiles: Dict[str, object]) -> set:
    """Muted accounts that are still muted — one order on the account and the
    mute lifts (and is cleared), which is Christina's "settings revert to
    normal"."""
    live = set()
    for code, m in mutes.load_all().items():
        profile = profiles.get(code)
        if profile is None:                       # code no longer in the data
            live.add(code)
        elif m.lifted_by(last_order(profile)):
            mutes.remove(code)
        else:
            live.add(code)
    return live


def ranked() -> List[Attention]:
    """Every active customer, in queue order."""
    now = datetime.now(timezone.utc)
    notes = latest_updates()
    profiles = all_profiles()
    muted = _muted_codes(profiles)
    return sorted((_assess(p, notes.get(code), code in muted, now)
                   for code, p in profiles.items()),
                  key=Attention.sort_key)


def attention_payload(n: int = ATTENTION_QUEUE_SIZE) -> dict:
    everyone = ranked()
    queue = []
    for a in [a for a in everyone if a.reason is not AttentionReason.MUTED][:n]:
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
        "muted": sum(1 for a in everyone if a.reason is AttentionReason.MUTED),
        "snooze_days": NOTE_SNOOZE_DAYS,
    }


# --- muting ----------------------------------------------------------------

def mute_customer(code: str, note: str = "") -> bool:
    """Stop alerting on this account until an order lands on it."""
    profile = all_profiles().get(code)
    mutes.save(code, last_order(profile) if profile else None, note)
    return True


def unmute_customer(code: str) -> bool:
    return mutes.remove(code)
