"""Live customer intelligence (WhatsApp dumps, notes typed by a rep).

An `IntelUpdate` is one summarised message about one customer. Updates are
layered on top of the static `MEETING_NOTES` baseline (see utils/intel.py) so
"What's going on" and the pitch pool reflect the latest conversation.
"""
from enum import Enum

from constants.rfm import RelationshipFlag


class IntelSource(Enum):
    WHATSAPP = "whatsapp"
    MANUAL = "manual"


# Newest live hooks shown ahead of the baseline; keep the card readable.
MAX_LIVE_HOOKS = 3
MAX_TOTAL_HOOKS = 5

# Ranking bump for opportunity candidates that came from a live update
# (on top of the meeting-notes bump), so fresh intel surfaces first.
LIVE_OPPORTUNITY_BONUS = 8.0
# When the latest update flags the relationship, tilt the ranking towards
# save-the-account / relationship actions and away from hard selling.
LIVE_CHURN_RETENTION_BOOST = 1.5
LIVE_CHURN_SELL_DEMOTE = 0.75

# Model used by the summariser (override with SEARAY_INTEL_MODEL).
DEFAULT_INTEL_MODEL = "claude-opus-5"
INTEL_MAX_TOKENS = 4000

# Relationship signals the summariser may emit — must be RelationshipFlag names.
RELATIONSHIP_SIGNALS = tuple(f.name for f in RelationshipFlag if f is not RelationshipFlag.NONE) + ("UNCHANGED",)
UNCHANGED = "UNCHANGED"


def extraction_schema(customer_codes, group_names) -> dict:
    """JSON schema for one summariser call: a list of per-customer extractions.
    `customer_code` is constrained to the POC customers (or null = unmatched)."""
    return {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "customer_code": {"type": ["string", "null"], "enum": list(customer_codes) + [None]},
                        "customer_as_written": {"type": "string"},
                        "hooks": {"type": "array", "items": {"type": "string"}},
                        "opportunity_groups": {"type": "array", "items": {"type": "string", "enum": list(group_names)}},
                        "referenced_products": {"type": "array", "items": {"type": "string"}},
                        "prior_incentive": {"type": "string"},
                        "relationship": {"type": "string", "enum": list(RELATIONSHIP_SIGNALS)},
                        "next_contact": {"type": "string"},
                        "advice": {"type": "string"},
                    },
                    "required": ["customer_code", "customer_as_written", "hooks", "opportunity_groups",
                                 "referenced_products", "prior_incentive", "relationship",
                                 "next_contact", "advice"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["updates"],
        "additionalProperties": False,
    }
