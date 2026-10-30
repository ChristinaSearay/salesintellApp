"""Search the synced catalogue for the View Products list.

Quantities here are as of the last sync; the product page asks Unleashed live
(utils/stock.py). Every word typed must appear in the code or description, so
"18k bolt ring" narrows rather than widens.
"""
from typing import List

from constants.stock import PRODUCT_PAGE_SIZE
from utils.products import CatalogueItem


def _matches(item: CatalogueItem, words: List[str]) -> bool:
    haystack = f"{item.code} {item.description}".lower()
    return all(w in haystack for w in words)


def _rank(item: CatalogueItem, query: str):
    """Exact code first, then codes starting with what was typed, then newest."""
    code = item.code.lower()
    return (code != query, not code.startswith(query),
            -(item.created_on.toordinal() if item.created_on else 0))


def _row(item: CatalogueItem) -> dict:
    return {
        "code": item.code,
        "description": item.description,
        "group": item.group,
        "on_hand": item.on_hand,
        "available": item.available,
        "created_on": item.created_on.isoformat() if item.created_on else None,
    }


def search_products(items: List[CatalogueItem], groups: List[str], query: str,
                    group: str, in_stock_only: bool, page: int) -> dict:
    if group and group not in groups:
        raise ValueError(f"Unknown product group: {group}")
    if page < 0:
        raise ValueError("Page must be 0 or more.")
    q = (query or "").strip().lower()
    words = q.split()
    found = [i for i in items
             if (not group or i.group == group)
             and (not in_stock_only or i.in_stock)
             and _matches(i, words)]
    found.sort(key=lambda i: _rank(i, q))
    page_count = max(1, -(-len(found) // PRODUCT_PAGE_SIZE))
    page = min(page, page_count - 1)
    start = page * PRODUCT_PAGE_SIZE
    return {
        "items": [_row(i) for i in found[start:start + PRODUCT_PAGE_SIZE]],
        "total": len(found),
        "page": page,
        "page_count": page_count,
        "groups": groups,
    }
