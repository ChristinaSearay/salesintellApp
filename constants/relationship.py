"""Which relationship flags are claims the order history can overturn.

A relationship flag is qualitative: it comes from a meeting note, or from a
WhatsApp update the summariser read. The order history is objective. When the
two disagree about whether a customer is still engaged, the numbers win — a
shop that ordered inside its usual gap has not "gone quiet on us", whatever a
chat thread said months ago.

CHURN_RISK is deliberately NOT in here. A customer can order every week and
still be telling us they are finished with us — Class A place orders weekly
after saying they would never deal with Searay again — so no amount of buying
disproves it. Same for OCCASIONAL: "orders only as needed" is a description of
how they buy, not a claim that they stopped.
"""
from constants.rfm import RelationshipFlag

# Flags asserting the customer stopped engaging with us. Each is suppressed
# while that customer's own ordering rhythm says otherwise.
QUIET_CLAIMS = frozenset({
    RelationshipFlag.STALLED,       # "relationship cooled, no recent selling effort"
    RelationshipFlag.DECLINING,     # "order frequency / value dropping"
    RelationshipFlag.DORMANT_PROSPECT,  # "engaged well but never converted"
})
