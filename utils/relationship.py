"""Keep a qualitative relationship flag honest against the order history.

Christina, on a Champion account that ordered a fortnight ago still badged
"Gone quiet on us": "Why is it still saying gama has gone quiet". The flag had
come from a WhatsApp thread about a diamond bangle quote Michelle was waiting
on — the customer was waiting on *us*, which the summariser read as the
relationship cooling. Nothing then checked that against the fact that they had
ordered $58k eight days later.

The rule: a flag claiming a customer went quiet is dropped while they are still
ordering inside their own rhythm. It is not deleted from the note, and it comes
back by itself the moment they actually go quiet — same self-healing shape as
`utils/mute.py`, which lifts when a newer order lands.
"""
from typing import Optional

from constants.relationship import QUIET_CLAIMS
from constants.rfm import RelationshipFlag
from utils.rhythm import rhythm_days, within_rhythm


def effective_flag(flag: RelationshipFlag, order_dates,
                   recency_days: Optional[int]) -> RelationshipFlag:
    """The flag to show, given what the customer has actually been ordering.

    Anything outside QUIET_CLAIMS passes through untouched, as does a customer
    with too little history to have a rhythm — two orders is one gap, which is
    no evidence either way.
    """
    if flag not in QUIET_CLAIMS:
        return flag
    if within_rhythm(rhythm_days(order_dates), recency_days):
        return RelationshipFlag.NONE
    return flag


def flag_for(profile, notes) -> RelationshipFlag:
    """The flag to show for a profile, re-reading the note.

    The API layer can't just use `profile.relationship`: profiles are built once
    per process and cached, while notes are read fresh on every request so a
    WhatsApp update saved mid-session shows up without a restart. That re-read
    has to come back through this guard, or a freshly saved note walks straight
    past it — which is how Gama kept its badge.
    """
    flag = notes.relationship if notes else profile.relationship
    return effective_flag(flag, profile.order_dates, profile.recency_days)
