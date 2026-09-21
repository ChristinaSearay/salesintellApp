"""The "needs attention" queue on the accounts screen (utils/attention.py).

Order: customers late against their own ordering rhythm, then everyone else
not noted recently — biggest 2-year spend first within each — then customers
with a recent note, oldest note first (a note sends them to the back of the line).

Calibrated on the live Unleashed data (17 Sep 2026): 114 of 562 active
customers are overdue on these settings.
"""
from enum import Enum

# How many customers the queue shows at once.
ATTENTION_QUEUE_SIZE = 5

# A rhythm needs at least this many separate order dates (two gaps).
MIN_RHYTHM_ORDER_DATES = 3
# Overdue = days since the last order is at least this multiple of their usual gap...
OVERDUE_RATIO = 1.5
# ...and at least this many days past it, so weekly buyers a few days late don't flag.
MIN_OVERDUE_DAYS = 14

# A note (typed on the queue, or a confirmed WhatsApp update) parks the
# customer at the back of the line for this long.
NOTE_SNOOZE_DAYS = 30

# A muted account's watermark when they had never ordered: any first order
# lifts the mute (utils/mute.py).
NO_ORDER_MARK = ""


class AttentionReason(Enum):
    """Why a customer sits where they do in the queue — also the sort tier."""
    OVERDUE = "overdue"
    NO_RECENT_NOTE = "no_recent_note"
    RECENTLY_NOTED = "recently_noted"
    MUTED = "muted"          # "do not alert again" — out of the queue entirely


TIER_ORDER = {
    AttentionReason.OVERDUE: 0,
    AttentionReason.NO_RECENT_NOTE: 1,
    AttentionReason.RECENTLY_NOTED: 2,
    AttentionReason.MUTED: 3,
}
