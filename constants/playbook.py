"""The rep playbook: ideas a rep came up with themselves, reused on customers
in the same situation (utils/playbook.py).

The learning loop already reads rejections (constants/feedback.py) but only
ever per customer. This is the other half Christina asked for: when a rep
ignores the suggested pitches and does something of their own, record it and
offer it to similar shops.

"Similar" is deliberately narrow — same RFM segment AND at least one product
group in common — because a pitch that works on an at-risk chain-buyer is not
evidence about a champion who only buys findings.
"""
from enum import Enum

# What a rep types. A title is the pitch in one line; detail is optional.
MIN_IDEA_LENGTH = 4
MAX_IDEA_LENGTH = 120
MAX_DETAIL_LENGTH = 600

# How many of the origin customer's product groups an idea is filed against
# (biggest spend first) — "the range they buy".
IDEA_GROUPS = 3
# A borrowed idea needs this many groups in common with the new customer.
MIN_SHARED_GROUPS = 1

# At most this many borrowed ideas enter one customer's pool, so the playbook
# can never crowd out the engine's own pitches.
MAX_BORROWED_IDEAS = 2
# The rep's own ideas, on the customer they were written for.
MAX_OWN_IDEAS = 3

# Where a fresh idea enters the ranking: above a plain upsell, below a
# retention play or a hand-authored seed (KIND_BASE_SCORE in constants/feedback.py).
IDEA_BASE_SCORE = 70.0

# Candidate ids are "<customer code><marker><idea id>", so a tap on a card can
# be traced back to the idea it came from.
IDEA_ID_MARKER = "-idea-"

# Confidence: every accept makes an idea travel further, every skip pulls it
# back, and an idea nobody takes up retires itself.
CONFIDENCE_START = 1.0
ACCEPT_STEP = 0.15
REJECT_STEP = 0.20
MAX_CONFIDENCE = 1.6
MIN_CONFIDENCE = 0.3
# Below this an idea stops being offered to anyone new.
RETIRE_BELOW = 0.5


class IdeaField:
    """Keys in a stored idea (playbook/<id>.json)."""
    ID = "id"
    TITLE = "title"
    DETAIL = "detail"
    GROUPS = "groups"
    SEGMENT = "segment"
    ORIGIN_CODE = "origin_code"
    ORIGIN_NAME = "origin_name"
    TS = "ts"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class IdeaOrigin(Enum):
    """Why this idea is on the screen."""
    OWN = "own"            # written for this customer
    BORROWED = "borrowed"  # written elsewhere, same situation
