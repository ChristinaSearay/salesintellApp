"""RFM scoring and segment assignment.

Pure functions over numbers + the band/segment constants. No I/O.
"""
from typing import Optional

from constants.rfm import (
    FREQUENCY_BANDS,
    MONETARY_BANDS,
    R_DORMANT,
    RECENCY_BANDS,
    RF_HIGH,
    RF_LOW,
    RF_MID,
    SCORE_MIN,
    Segment,
)


def score_recency(days: Optional[int]) -> int:
    """Fewer days since last order => higher score."""
    if days is None:
        return SCORE_MIN
    for score, max_days in RECENCY_BANDS:
        if days <= max_days:
            return score
    return SCORE_MIN


def score_frequency(orders: int) -> int:
    for score, min_orders in FREQUENCY_BANDS:
        if orders >= min_orders:
            return score
    return SCORE_MIN


def score_monetary(dollars: float) -> int:
    for score, min_dollars in MONETARY_BANDS:
        if dollars >= min_dollars:
            return score
    return SCORE_MIN


def rfm_segment(r: int, f: int) -> Segment:
    """Map Recency + Frequency scores to a segment (Monetary is a value tier,
    not a segment driver). Precedence matters; branches are mutually exclusive."""
    if r >= RF_HIGH and f >= RF_HIGH:
        return Segment.CHAMPION
    if r == R_DORMANT:
        return Segment.HIBERNATING
    if r in (RF_LOW, RF_MID) and f >= RF_MID:
        return Segment.AT_RISK
    if r in (RF_LOW, RF_MID) and f <= RF_LOW:
        return Segment.ABOUT_TO_SLEEP
    if r >= RF_HIGH and f == RF_MID:
        return Segment.LOYAL
    if r >= RF_HIGH and f <= RF_LOW:
        return Segment.POTENTIAL_LOYALIST
    # Fallback (e.g. r==RF_MID, f==RF_MID handled above): treat as Loyal.
    return Segment.LOYAL
