"""Enums + scoring constants for the rejection -> re-suggestion learning loop.

A rep rejects an action and taps one or more REASON chips. Each reason maps to a
deterministic effect on that customer's saved preference profile (see
utils/preferences.py), which re-ranks a candidate pool (utils/candidates.py).
Everything is rule-based and traceable — no raw strings/ints in the logic.
"""
from enum import Enum


# --- Price banding (for the "too expensive" signal) ------------------------
PRICE_LOW_MAX = 500.0
PRICE_MID_MAX = 2000.0


class PriceBand(Enum):
    LOW = 0
    MID = 1
    HIGH = 2

    @property
    def rank(self) -> int:
        return self.value


def price_band(price: float) -> PriceBand:
    if price <= PRICE_LOW_MAX:
        return PriceBand.LOW
    if price <= PRICE_MID_MAX:
        return PriceBand.MID
    return PriceBand.HIGH


# --- What sort of action a candidate is ------------------------------------
class ActionKind(Enum):
    RETENTION = "Retention"
    UPSELL = "Upsell"
    WHITESPACE = "New category"
    RELATIONSHIP = "Relationship"
    STRUCTURAL = "Commercial terms"
    EQUIPMENT = "Equipment"
    GENERAL = "General"


# --- Incentive types (so "no discounts" can filter precisely) --------------
class IncentiveType(Enum):
    NONE = "None"
    GOODWILL = "Goodwill / credit"
    DISCOUNT = "Discount"
    REBATE = "Volume rebate"
    PRICE_MATCH = "Price match"
    SALE_OR_RETURN = "Sale or return"
    CONSIGNMENT = "Consignment"
    DEMO = "Demo / trial"


# Incentive types that count as "a discount" for the No-discounts signal.
DISCOUNT_LIKE = frozenset({
    IncentiveType.DISCOUNT,
    IncentiveType.REBATE,
    IncentiveType.PRICE_MATCH,
})


# --- Rejection reasons (the tappable chips) --------------------------------
class RejectionReason(Enum):
    #            icon   short label (chip)            longer help
    TOO_EXPENSIVE = ("💲", "Too expensive", "Lower the price of what we suggest")
    WRONG_PRODUCT = ("🚫", "They don't sell this", "Avoid this product type")
    ALREADY_HAVE = ("📦", "Already buys it", "They already stock this")
    TRIED_BEFORE = ("🔁", "Tried this before", "We've already pitched this")
    NO_INCENTIVES = ("🏷️", "No discounts", "Avoid discount-based offers")
    TOO_PUSHY = ("🤝", "Too pushy now", "Keep it low-pressure / relationship-first")
    BAD_TIMING = ("⏳", "Not right now", "Timing is off — show different ideas")
    WANT_OTHER = ("🔀", "Show me others", "Just give me different options")

    def __init__(self, icon: str, label: str, help_text: str):
        self.icon = icon
        self.label = label
        self.help_text = help_text


# --- Scoring constants -----------------------------------------------------
SEED_BASE_SCORE = 100.0  # the hand-authored actions start on top

# Base score for auto-generated candidates by kind.
KIND_BASE_SCORE = {
    ActionKind.RETENTION: 75.0,
    ActionKind.EQUIPMENT: 68.0,
    ActionKind.UPSELL: 65.0,
    ActionKind.STRUCTURAL: 60.0,
    ActionKind.WHITESPACE: 55.0,
    ActionKind.RELATIONSHIP: 50.0,
    ActionKind.GENERAL: 40.0,
}

# Multipliers applied to a kind's weight when a reason asks for it.
PUSHY_DEMOTE = 0.3          # upsell/whitespace when "too pushy"
PUSHY_PROMOTE = 1.6         # relationship/retention when "too pushy"
TIMING_DEMOTE = 0.6        # the rejected kind when "not right now"
VARIETY_DEMOTE = 0.7       # the rejected kind when "show me others"
