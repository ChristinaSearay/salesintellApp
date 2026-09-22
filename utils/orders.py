"""Which sales-order lines count as a real order.

Status alone isn't enough: a Parked order is normally a draft, but the team
also invoices straight off parked orders, and an invoiced order is a sale
whatever status it was left in. The invoice is matched to its order by number
(constants/columns.py:DocPrefix) — 3,493 of 3,499 completed orders pair up
that way, always with the same customer.
"""
from functools import lru_cache

from constants.columns import DocPrefix, InvoiceCol, SalesCol, SalesStatus
from utils.datasource import invoice_rows


def order_no_for_invoice(invoice_no: str) -> str:
    """SI-00094003 -> SO-00094003; web#3181 -> web#3181."""
    invoice_no = (invoice_no or "").strip()
    if invoice_no.startswith(DocPrefix.INVOICE):
        return DocPrefix.SALES_ORDER + invoice_no[len(DocPrefix.INVOICE):]
    return invoice_no


@lru_cache(maxsize=1)
def invoiced_order_numbers() -> frozenset:
    """Every order number that has an invoice. Cached per process."""
    return frozenset(
        order_no_for_invoice(row.get(InvoiceCol.TRANSACTION_NO)) for row in invoice_rows()
    )


def counts_as_order(row: dict) -> bool:
    """True for a committed order line, or a parked one that was invoiced."""
    status = row.get(SalesCol.STATUS)
    if status in SalesStatus.COUNTED:
        return True
    return (status in SalesStatus.COUNTED_ONCE_INVOICED
            and (row.get(SalesCol.ORDER_NO) or "").strip() in invoiced_order_numbers())
