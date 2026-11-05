"""A product's sell price tiers, read from the Unleashed Product object.

The product page already fetches the full Product to show its name and photo,
and the tiers ride along in it, so prices cost no extra request. Cost fields
(purchase price, average land price, last cost) are never read here.
"""
from constants.pricing import PRICE_TIER_FIELD, PRICE_TIER_SLOTS, SHOWN_PRICE_TIERS
from utils.parsing import parse_money


def _tiers_by_name(product: dict) -> dict:
    """Unleashed tier name -> raw value, across all ten slots."""
    tiers = {}
    for slot in PRICE_TIER_SLOTS:
        tier = product.get(PRICE_TIER_FIELD.format(slot)) or {}
        name = (tier.get("Name") or "").strip()
        if name:
            tiers[name] = tier.get("Value")
    return tiers


def price_tiers(product: dict) -> list:
    """The tiers in SHOWN_PRICE_TIERS, in that order, as {name, price}.

    `price` is None when the product has no price in that tier, or when no
    tier carries that name in Unleashed any more; the page says "Not set"
    either way rather than hiding the row.
    """
    tiers = _tiers_by_name(product)
    rows = []
    for name in SHOWN_PRICE_TIERS:
        value = tiers.get(name)
        blank = value is None or (isinstance(value, str) and not value.strip())
        rows.append({"name": name, "price": None if blank else parse_money(value)})
    return rows
