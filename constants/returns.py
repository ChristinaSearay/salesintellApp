"""Returns / credit notes — how much a customer sends back.

Spend is invoiced MINUS credits (Christina, 18 Sep 2026: "the spend should be
the amount actually invoiced minus credits. Not orders. This is inflated. This
customer orders and then returns a lot of stock"). Across 24 months credits run
at ~21% of everything invoiced, so gross invoiced is not a usable number.

The return rate is worth showing in its own right: a shop that sends back most
of what it buys should not be pitched more stock to sit on.
"""

# Net spend can't go below zero. A customer who returns goods invoiced BEFORE
# the 24-month window shows more credits than invoices inside it — a windowing
# artifact, not a customer who owes us product. "-$8,000 spend · 2yr" reads as
# a bug to a rep, so the floor is zero.
MIN_NET_SPEND = 0.0

# Below this much invoiced, a return rate is noise — one returned parcel on a
# two-order history is 100% and says nothing about how they buy.
MIN_INVOICED_FOR_RATE = 2_000.0

# Show the returns flag at/above this share of invoiced value sent back.
HIGH_RETURN_RATE = 0.30
