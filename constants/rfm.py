"""RFM scoring bands, segment definitions, and relationship flags.

Bands are ABSOLUTE business thresholds, not quintiles: with only a handful of
customers, quintile scoring is degenerate and unstable as the base grows. These
thresholds reflect a wholesale jeweller's reorder cadence and deal sizes, and
were signed off by the business owner.
"""
from enum import Enum

SCORE_MIN = 1
SCORE_MAX = 5

# --- Band tables -----------------------------------------------------------
# Recency: fewer days since last order is better. (score, max_days_inclusive),
# evaluated best-to-worst; anything beyond the last bound scores SCORE_MIN.
RECENCY_BANDS = ((5, 30), (4, 90), (3, 180), (2, 365))

# Frequency: distinct orders in the window. (score, min_orders_inclusive).
FREQUENCY_BANDS = ((5, 24), (4, 12), (3, 6), (2, 2))

# Monetary: gross invoiced (AUD) in the window. (score, min_dollars_inclusive).
MONETARY_BANDS = ((5, 150_000), (4, 75_000), (3, 25_000), (2, 5_000))


# --- Segments --------------------------------------------------------------
class Segment(Enum):
    CHAMPION = "Champion"
    LOYAL = "Loyal"
    POTENTIAL_LOYALIST = "Potential Loyalist"
    AT_RISK = "At Risk"
    ABOUT_TO_SLEEP = "About to Sleep"
    HIBERNATING = "Hibernating / Lost"


# Score thresholds used by the segment grid (named, not magic).
RF_HIGH = 4   # recent / frequent
RF_MID = 3
RF_LOW = 2
R_DORMANT = 1


# --- Relationship overlay (from meeting notes) -----------------------------
# Per business decision, the objective RFM segment is kept and a qualitative
# relationship flag is shown ALONGSIDE it (never overwriting the score).
class RelationshipFlag(Enum):
    CHURN_RISK = "Churn risk — actively disengaging / threatening to leave"
    STALLED = "Stalled — relationship cooled, no recent selling effort"
    DECLINING = "Declining — order frequency / value dropping"
    DORMANT_PROSPECT = "Dormant prospect — engaged well but never converted"
    OCCASIONAL = "Occasional buyer — orders only as needed"
    NONE = ""
