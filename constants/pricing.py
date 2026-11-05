"""Sell price tiers shown on a product page.

Unleashed keeps ten sell price slots per product (SellPriceTier1..10), each
carrying its own name as set in Unleashed → Settings. The tiers are picked by
that name, not by slot number, so moving a tier to another slot in Unleashed
doesn't show the wrong price under the right heading.

As of 05 Nov 2026: 1 RRP, 3 Exclusive (= the default sell price), 4 Buying
Group (Exclusive less 5%), 5 VIP (Exclusive less 10%), 10 Web Exclusive; the
rest are unnamed. Christina asked for Exclusive, Buying Group and VIP.
"""

# Display order on the product page.
SHOWN_PRICE_TIERS = ("Exclusive", "Buying Group", "VIP")

# Unleashed's SellPriceTier1 .. SellPriceTier10.
PRICE_TIER_FIELD = "SellPriceTier{}"
PRICE_TIER_SLOTS = range(1, 11)
