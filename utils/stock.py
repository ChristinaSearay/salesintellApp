"""Live stock for one product, warehouse by warehouse, straight from Unleashed.

Unleashed's own all-warehouses call only reports *available* per warehouse;
the rep needs on hand, hence one StockOnHand/<guid>?warehouseCode=<w> call per
warehouse, all in parallel (~3s — Unleashed answers each in 1-3s). The product
Guid and the warehouse list are remembered so a product only pays for that
one round: Guids never change, and warehouses are re-read hourly. The totals
are the sum of the warehouse rows rather than another (slower) request, so
they always agree with the breakdown. Cost stays out: reps don't see it.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache

from constants.stock import (
    GROUP_ORDER,
    LIVE_STOCK_WORKERS,
    WAREHOUSE_GROUPS,
    WAREHOUSE_LIST_TTL_SECONDS,
    WarehouseGroup,
)
from constants.unleashed import Endpoint
from utils import unleashed as api
from utils.parsing import parse_number

QUANTITIES = ("on_hand", "allocated", "available", "on_purchase")

_warehouses: dict = {"rows": [], "fetched": 0.0}
_warehouses_lock = threading.Lock()


@lru_cache(maxsize=4096)
def _product_guid(code: str) -> str:
    """The product's Unleashed Guid.

    Unleashed ignores a productCode it doesn't recognise and returns the whole
    stock list instead, so the exact code has to be picked out of the result.
    A LookupError isn't cached, so a product created later is found next time.
    """
    items = api.get_one(f"{Endpoint.STOCK_ON_HAND}/Page/1", {"productCode": code}).get("Items", [])
    match = next((s for s in items if s.get("ProductCode") == code), None)
    if match is None:
        raise LookupError(f"{code} isn't in Unleashed.")
    return match["ProductGuid"]


def _active_warehouses() -> list:
    with _warehouses_lock:
        if time.monotonic() - _warehouses["fetched"] > WAREHOUSE_LIST_TTL_SECONDS:
            _warehouses["rows"] = [w for w in api.fetch_all(Endpoint.WAREHOUSES)
                                   if not w.get("Obsolete")]
            _warehouses["fetched"] = time.monotonic()
        return _warehouses["rows"]


def _warehouse_stock(guid: str, warehouse: dict) -> dict:
    s = api.get_one(f"{Endpoint.STOCK_ON_HAND}/{guid}", {"warehouseCode": warehouse["WarehouseCode"]})
    return {
        "code": warehouse["WarehouseCode"],
        "name": warehouse.get("WarehouseName", ""),
        "on_hand": parse_number(s.get("QtyOnHand")),
        "allocated": parse_number(s.get("AllocatedQty")),
        "available": parse_number(s.get("AvailableQty")),
        "on_purchase": parse_number(s.get("OnPurchase")),
    }


def _holds_stock(row: dict) -> bool:
    return any(row[k] for k in ("on_hand", "allocated", "available"))


def group_warehouses(rows: list) -> list:
    """Warehouses that hold any of the product, under their rep-facing heading."""
    grouped = []
    for group in GROUP_ORDER:
        members = [r for r in rows
                   if WAREHOUSE_GROUPS.get(r["code"], WarehouseGroup.UNSORTED) is group
                   and _holds_stock(r)]
        if members:
            grouped.append({
                "group": group.name,
                "label": group.value,
                "on_hand": sum(r["on_hand"] for r in members),
                "warehouses": sorted(members, key=lambda r: r["name"]),
            })
    return grouped


def _image(product: dict) -> str:
    images = product.get("Images") or []
    default = next((i.get("Url") for i in images if i.get("IsDefault")), None)
    return default or product.get("ImageUrl") or ""


def _group_name(product: dict) -> str:
    group = product.get("ProductGroup") or {}
    return group.get("GroupName", "") if isinstance(group, dict) else str(group)


def live_product(code: str) -> dict:
    """Everything the product page shows, fetched now. Raises LookupError for an
    unknown code and RuntimeError when Unleashed can't be reached or refuses."""
    code = (code or "").strip()
    if not code:
        raise ValueError("No product code given.")
    with ThreadPoolExecutor(max_workers=LIVE_STOCK_WORKERS) as pool:
        guid_job = pool.submit(_product_guid, code)
        warehouses_job = pool.submit(_active_warehouses)
        guid, warehouses = guid_job.result(), warehouses_job.result()
        product_job = pool.submit(api.get_one, f"{Endpoint.PRODUCTS}/{guid}")
        rows = list(pool.map(lambda w: _warehouse_stock(guid, w), warehouses))
        product = product_job.result()
    return {
        "code": code,
        "description": product.get("ProductDescription", ""),
        "group": _group_name(product),
        "image": _image(product),
        "obsolete": bool(product.get("Obsolete")),
        "totals": {q: sum(r[q] for r in rows) for q in QUANTITIES},
        "warehouses": group_warehouses(rows),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
