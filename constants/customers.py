"""The five target customers for the POC.

`balance_owing` is a MANUAL input: Unleashed has no clean export for customer
balance (confirmed in the project's Data Summary), so head office supplied these
figures. Only Class A currently owes money.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetCustomer:
    code: str
    name: str
    balance_owing: float  # AUD; manual input, not derivable from the exports


# Codes are the Unleashed customer codes. Noonan's resolved to S141 from the data
# ("SC- Noonan's Showcase Jewellers").
TARGET_CUSTOMERS = (
    TargetCustomer("CMJ223", "Class A Manufacturing Jewellers", 2862.0),
    TargetCustomer("AJW093", "Atlas Jewellers - Wetherill Park", 0.0),
    TargetCustomer("MJ001", "My Jewellers", 0.0),
    TargetCustomer("TCJ1138", "The Cut Jewellery", 0.0),
    TargetCustomer("S141", "Noonan's Showcase Jewellers", 0.0),
)

TARGET_BY_CODE = {c.code: c for c in TARGET_CUSTOMERS}
TARGET_CODES = frozenset(TARGET_BY_CODE)
