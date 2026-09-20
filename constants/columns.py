"""Column-name constants for each export, so no raw header strings appear in
logic. File 1's required columns carry a leading asterisk in the header.
"""


class SalesCol:
    """File 3 - Sales Enquiry Export (orders)."""
    CUSTOMER_CODE = "Customer Code"
    PRODUCT_CODE = "Product Code"
    PRODUCT = "Product"
    ORDER_NO = "Order No."
    ORDER_DATE = "Order Date"
    PRODUCT_GROUP = "Product Group"
    PRODUCT_SUB_GROUP = "Product Sub Group"
    STATUS = "Status"
    QUANTITY = "Quantity"
    SUB_TOTAL = "Sub Total"
    CONTACT_NAME = "Contact Name"
    CONTACT_PHONE = "Contact Phone"
    CONTACT_EMAIL = "Contact Email"


class CustomerCol:
    """Customers cache (data/customers.json) — Unleashed sync only; there is no
    matching CSV export, so CSV mode falls back to the order-row contact."""
    CODE = "Customer Code"
    NAME = "Customer Name"
    CONTACT_NAME = "Contact Name"
    PHONE = "Phone"
    MOBILE = "Mobile"
    EMAIL = "Email"


class InvoiceCol:
    """File 4 - Invoice Enquiry Export (spend)."""
    TRANSACTION_NO = "Transaction No."
    COMPLETED_DATE = "Completed Date"
    CUSTOMER_CODE = "Customer Code"
    CUSTOMER_NAME = "Customer Name"
    TOTAL = "Total"


class ProductCol:
    """File 1 - Products Export (product master / taxonomy)."""
    CODE = "*Product Code"
    DESCRIPTION = "*Product Description"
    GROUP = "Product Group"
    SUB_GROUP = "Product Sub Group"
    SELL_PRICE = "Default Sell Price"


class ViewCol:
    """File 2 - View Products Export (new products + live stock)."""
    CODE = "Product Code"
    SUPPLIER = "Supplier Name"
    DESCRIPTION = "Product Description"
    CREATED_ON = "Created On"
    SELL_PRICE = "Default Sell Price"
    ON_HAND = "On Hand"
    AVAILABLE = "Available"


# Sentinel values found in the data (not magic strings in logic).
class SalesStatus:
    COMPLETED = "Completed"
    BACKORDERED = "Backordered"   # committed, waiting on stock — often the big ones
    PLACED = "Placed"             # committed, not yet picked
    PARKED = "Parked"             # a draft/quote the customer hasn't committed to
    TOTALS_FOOTER = "Totals"  # a stray summary row to ignore

    # What counts as "they ordered" for recency, order counts and the
    # needs-attention queue. Backorders and placed orders are real commitments,
    # so excluding them made big customers look lapsed the week they ordered
    # (Evans Jewellery, $58k backordered 08/09/2026). Parked is a draft, so it
    # stays out. An allow-list, so any unexpected status is excluded by default.
    COUNTED = frozenset({COMPLETED, BACKORDERED, PLACED})
