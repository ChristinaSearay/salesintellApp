"""Product-group rules for the upsell engine.

- "Misc" is a 2,705-product catch-all that also holds freight / non-stock
  charges (the NON-STOCK ITEM code maps to it). It is excluded from the
  buys-from / pitch-from analysis as noise.
- A few group names are entered inconsistently in Unleashed; GROUP_ALIASES
  folds the variants onto a single canonical name so matches don't slip
  through the cracks.
"""
from enum import Enum

# Groups that are not real merchandising categories.
EXCLUDED_GROUPS = frozenset({"Misc", ""})

# Product codes that are charges/placeholders rather than stock items.
EXCLUDED_PRODUCT_CODES = frozenset({"NON-STOCK ITEM"})

# Inconsistent group spellings -> canonical name (verified against File 1).
GROUP_ALIASES = {
    "Cable|Trace|Oval Link": "Cable | Trace | Oval Link Chains",
    "Franco Chain": "Franco Chains",
    "Curb Chain": "Curb Chains",
}


class StockStatus(Enum):
    IN_STOCK = "In stock"
    BACKORDER = "Backorder"


# A new product counts as sellable-now when physical stock is on hand.
# Per business decision: lead with in-stock items, list the rest as backorder.
ON_HAND_IN_STOCK_MIN = 0  # On Hand strictly greater than this => in stock


def canonical_group(group: str) -> str:
    """Normalise a raw Product Group string to its canonical form."""
    g = (group or "").strip()
    return GROUP_ALIASES.get(g, g)
