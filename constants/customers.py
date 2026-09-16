"""Customer record + the five original POC customers.

Every customer with activity in the data is in the app (see utils/customers.py).
The POC five below keep their curated names and are the scope of the Markdown
reports and the analyze.py regression baseline.

`balance_owing` is a MANUAL input: Unleashed has no clean export for customer
balance (confirmed in the project's Data Summary), so head office supplied these
figures for the POC five. Everyone else defaults to 0.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Customer:
    code: str
    name: str
    balance_owing: float = 0.0  # AUD; manual input, not derivable from the exports


# Codes are the Unleashed customer codes. Noonan's resolved to S141 from the data
# ("SC- Noonan's Showcase Jewellers").
TARGET_CUSTOMERS = (
    Customer("CMJ223", "Class A Manufacturing Jewellers", 2862.0),
    Customer("AJW093", "Atlas Jewellers - Wetherill Park", 0.0),
    Customer("MJ001", "My Jewellers", 0.0),
    Customer("TCJ1138", "The Cut Jewellery", 0.0),
    Customer("S141", "Noonan's Showcase Jewellers", 0.0),
)

TARGET_BY_CODE = {c.code: c for c in TARGET_CUSTOMERS}
TARGET_CODES = frozenset(TARGET_BY_CODE)
