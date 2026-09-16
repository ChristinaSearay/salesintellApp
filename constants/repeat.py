"""Thresholds for the repeat-buying engine (utils/repeat.py).

Calibrated against the live Unleashed data (16 Sep 2026 sync, noise groups
excluded): 164 of 524 active customers repurchase the same product code, and
151 buy within the same product group on 3+ separate dates — so items need a
low bar to count as "repeat", while groups get a stricter one.
"""

# How many separate order dates make something a repeat purchase.
MIN_ITEM_PURCHASE_DATES = 2
MIN_GROUP_PURCHASE_DATES = 3

# Overdue = days since the last purchase divided by the usual interval.
# Items are pitched as soon as they are due; a group (a whole range) needs to
# be clearly overdue before it is worth raising.
ITEM_DUE_RATIO = 1.0
GROUP_DUE_RATIO = 1.2
# ...and the range must be visibly behind, not a couple of days over: "about
# every 2 weeks, last one 14 days ago" reads as a contradiction to a rep.
MIN_RESTOCK_OVERDUE_DAYS = 7
# Past this, they haven't just slipped — they've stopped, and the pitch changes.
LAPSED_RATIO = 3.0
# ...but only a line with a real history counts as "standing". Two orders give
# one gap, which is not a rhythm, so they never get the "they've stopped" framing.
MIN_LAPSED_PURCHASE_DATES = 4
# One "they've stopped" card is a useful warning; three in a row is a wall.
MAX_LAPSED_CARDS = 1
# A thin history gone quiet longer than this is stale, not due — don't pitch it
# as a reorder (the white-space/range cards still can).
MAX_DUE_DAYS = 365

# How many of each card can enter one customer's pool. Kept low so a rep's three
# cards are a mix, not three variations of the same idea.
MAX_REORDER = 2
MAX_GROUP_RESTOCK = 1
MAX_RANGE_EXTENSION = 3

# Range extension: which of their items to build "more like this" around, and
# how far from that item's price a sibling may sit (±40%).
RANGE_ANCHOR_ITEMS = 6
RANGE_PRICE_TOLERANCE = 0.4

# A whole range being overdue is a softer signal than a specific item being due.
GROUP_RESTOCK_PENALTY = 3.0

# Intervals up to this are phrased in weeks, longer ones in months.
WEEKS_PHRASE_MAX_DAYS = 70
