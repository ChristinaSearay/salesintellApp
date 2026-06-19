"""Pull data from Unleashed and write the local cache the engine reads.

The maps below turn Unleashed API objects into the SAME column-keyed rows the
CSV loaders produce (keys come from constants/columns.py), so nothing downstream
changes — the engine can't tell the difference.

⚠ The field names follow Unleashed's documented schema but MUST be verified
against a real response. Run `uv run sync` once with credentials, eyeball
data/*.json, and fix any VERIFY-marked field that's empty/wrong.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

from constants.columns import InvoiceCol, ProductCol, SalesCol, ViewCol
from constants.config import CACHE_DIR
from constants.unleashed import LOOKBACK_DAYS
from utils import unleashed as api


def _date(value) -> str:
    """Unleashed date → 'DD/MM/YYYY' (what the engine's parser expects)."""
    if not value:
        return ""
    s = str(value)
    m = re.search(r"/Date\((\d+)", s)  # Microsoft JSON: /Date(1623456789000)/
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).strftime("%d/%m/%Y")
    try:  # ISO 8601
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return s


def _group_name(product: dict) -> str:
    pg = (product or {}).get("ProductGroup") or {}
    return pg.get("GroupName", "") if isinstance(pg, dict) else str(pg)


def map_products(products: list) -> list:
    return [{
        ProductCol.CODE: p.get("ProductCode", ""),
        ProductCol.DESCRIPTION: p.get("ProductDescription", ""),
        ProductCol.GROUP: _group_name(p),
        ProductCol.SELL_PRICE: p.get("DefaultSellPrice", "") or "",
    } for p in products]


def map_view_products(stock: list, product_by_code: dict) -> list:
    rows = []
    for s in stock:
        code = s.get("ProductCode", "")
        p = product_by_code.get(code, {})
        rows.append({
            ViewCol.CODE: code,
            ViewCol.DESCRIPTION: s.get("ProductDescription", "") or p.get("ProductDescription", ""),
            ViewCol.CREATED_ON: _date(p.get("CreatedOn")),          # VERIFY: product creation date
            ViewCol.SELL_PRICE: p.get("DefaultSellPrice", "") or "",
            ViewCol.ON_HAND: s.get("QtyOnHand", 0),                 # VERIFY
            ViewCol.AVAILABLE: s.get("AvailableQty", 0),            # VERIFY (AvailableQty vs AvailableQuantity)
        })
    return rows


def map_sales(orders: list, product_by_code: dict) -> list:
    rows = []
    for o in orders:
        customer = o.get("Customer") or {}
        for line in (o.get("SalesOrderLines") or []):
            prod = line.get("Product") or {}
            code = prod.get("ProductCode", "")
            group = _group_name(prod) or _group_name(product_by_code.get(code, {}))
            rows.append({
                SalesCol.CUSTOMER_CODE: customer.get("CustomerCode", ""),
                SalesCol.PRODUCT_CODE: code,
                SalesCol.PRODUCT: prod.get("ProductDescription", ""),
                SalesCol.ORDER_NO: o.get("OrderNumber", ""),
                SalesCol.ORDER_DATE: _date(o.get("OrderDate")),
                SalesCol.PRODUCT_GROUP: group,
                SalesCol.STATUS: o.get("OrderStatus", ""),          # VERIFY: should read "Completed"
                SalesCol.QUANTITY: line.get("OrderQuantity", 0),
                SalesCol.SUB_TOTAL: line.get("LineTotal", 0),       # VERIFY: ex-tax line total
            })
    return rows


def map_invoices(invoices: list) -> list:
    rows = []
    for inv in invoices:
        customer = inv.get("Customer") or {}
        rows.append({
            InvoiceCol.TRANSACTION_NO: inv.get("InvoiceNumber", ""),
            InvoiceCol.COMPLETED_DATE: _date(inv.get("InvoiceDate")),   # VERIFY: InvoiceDate vs CompletedDate
            InvoiceCol.CUSTOMER_CODE: customer.get("CustomerCode", ""),
            InvoiceCol.CUSTOMER_NAME: customer.get("CustomerName", ""),
            InvoiceCol.TOTAL: inv.get("Total", 0),
        })
    return rows


def _start_date() -> str:
    """ISO date ~24 months back, for the order/invoice fetch filters."""
    return (datetime.now(tz=timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")


def _write(name: str, rows: list) -> None:
    with open(os.path.join(CACHE_DIR, name), "w", encoding="utf-8") as fh:
        json.dump(rows, fh)


def sync() -> None:
    """Fetch everything from Unleashed and write data/*.json."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    start = _start_date()

    products = api.fetch_products()
    product_by_code = {p.get("ProductCode", ""): p for p in products}
    stock = api.fetch_stock_on_hand()
    orders = api.fetch_sales_orders(start)
    invoices = api.fetch_invoices(start)

    _write("products.json", map_products(products))
    _write("view_products.json", map_view_products(stock, product_by_code))
    _write("sales.json", map_sales(orders, product_by_code))
    _write("invoices.json", map_invoices(invoices))

    print(f"Synced to {CACHE_DIR}/  —  products={len(products)} stock={len(stock)} "
          f"orders={len(orders)} invoices={len(invoices)} (since {start})")
    print("⚠ Eyeball data/*.json and fix any empty VERIFY-marked field, then set "
          "SEARAY_DATA_SOURCE=unleashed.")
