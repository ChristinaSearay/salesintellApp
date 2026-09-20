"""The customer directory: every customer with a completed order or an invoice
in the data (~24 months), not just the POC five.

Name precedence: curated POC name > customer master (Unleashed sync) > the
most recent invoice's customer name > the code itself.
"""
from functools import lru_cache
from typing import Dict

from constants.columns import CustomerCol, InvoiceCol, SalesCol, SalesStatus
from constants.customers import TARGET_BY_CODE, Customer
from utils.datasource import customer_rows, invoice_rows, sales_rows
from utils.parsing import parse_date
from utils.prospect_store import load_all as load_prospects


def _clean(value) -> str:
    return (value or "").strip()


@lru_cache(maxsize=1)
def load_customers() -> Dict[str, Customer]:
    """code -> Customer for every active customer. Cached per process."""
    # The POC five are always present, even once they age out of the 24-month
    # window (The Cut has): they are curated, and reports are built from them.
    codes = set(TARGET_BY_CODE)
    for row in sales_rows():
        code = _clean(row.get(SalesCol.CUSTOMER_CODE))
        if code and row.get(SalesCol.STATUS) in SalesStatus.COUNTED:
            codes.add(code)

    invoice_names: Dict[str, tuple] = {}  # code -> (date, name) of latest invoice
    for row in invoice_rows():
        code = _clean(row.get(InvoiceCol.CUSTOMER_CODE))
        if not code:
            continue
        codes.add(code)
        name = _clean(row.get(InvoiceCol.CUSTOMER_NAME))
        when = parse_date(row.get(InvoiceCol.COMPLETED_DATE))
        prev = invoice_names.get(code)
        if name and (prev is None or (when and (prev[0] is None or when > prev[0]))):
            invoice_names[code] = (when, name)

    master_names = {
        _clean(row.get(CustomerCol.CODE)): _clean(row.get(CustomerCol.NAME))
        for row in customer_rows()
    }

    # Businesses a rep created from a visit: no orders or invoices yet, so they
    # reach the directory the same way the curated five do once they age out.
    for code, record in load_prospects().items():
        codes.add(code)
        master_names.setdefault(code, _clean(record.get("name")))

    out: Dict[str, Customer] = {}
    for code in codes:
        if code in TARGET_BY_CODE:
            out[code] = TARGET_BY_CODE[code]
            continue
        name = master_names.get(code) or (invoice_names.get(code) or (None, ""))[1] or code
        out[code] = Customer(code, name)
    return out
