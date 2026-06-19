"""Unleashed API client — HMAC-signed, paginated reads (Python stdlib only).

Unleashed auth: every request carries two headers —
    api-auth-id         the API ID
    api-auth-signature  Base64( HMAC-SHA256( API_KEY, <query-string> ) )
where <query-string> is everything after the '?' (or '' when there are none).
The page number goes in the PATH ( /<Endpoint>/Page/<n> ), so it is not signed.
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError

from constants.unleashed import (
    API_ID,
    API_KEY,
    API_URL,
    PAGE_SIZE,
    RATE_LIMIT_PAUSE,
    Endpoint,
    has_credentials,
)


def signature(query_string: str) -> str:
    """Base64(HMAC-SHA256(API_KEY, query_string))."""
    digest = hmac.new(API_KEY.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _request(endpoint: str, page: int, params: dict) -> dict:
    # Sign exactly the query string we send (order doesn't matter as long as
    # they match — Unleashed re-signs the query string it receives).
    query = urllib.parse.urlencode(sorted((params or {}).items()))
    url = f"{API_URL}/{endpoint}/Page/{page}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, headers={
        "api-auth-id": API_ID,
        "api-auth-signature": signature(query),
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Unleashed {endpoint} page {page} → HTTP {exc.code}: {body}") from exc


def fetch_all(endpoint: str, params: dict | None = None) -> list:
    """Fetch every page of an endpoint and return the combined Items list."""
    if not has_credentials():
        raise RuntimeError(
            "Unleashed credentials missing — set UNLEASHED_API_ID and UNLEASHED_API_KEY.")
    params = dict(params or {})
    params.setdefault("pageSize", PAGE_SIZE)

    items, page, pages = [], 1, 1
    while page <= pages:
        data = _request(endpoint, page, params)
        items.extend(data.get("Items", []))
        pages = (data.get("Pagination") or {}).get("NumberOfPages", 1)
        page += 1
        if page <= pages:
            time.sleep(RATE_LIMIT_PAUSE)
    return items


# --- per-endpoint helpers (param names marked VERIFY need a live check) -----

def fetch_products() -> list:
    return fetch_all(Endpoint.PRODUCTS)


def fetch_stock_on_hand() -> list:
    return fetch_all(Endpoint.STOCK_ON_HAND)


def fetch_sales_orders(start_date: str | None = None) -> list:
    params = {"orderStatus": "Completed"}          # VERIFY filter name/values
    if start_date:
        params["startDate"] = start_date            # VERIFY filter name
    return fetch_all(Endpoint.SALES_ORDERS, params)


def fetch_invoices(start_date: str | None = None) -> list:
    params = {}
    if start_date:
        params["startDate"] = start_date            # VERIFY filter name
    return fetch_all(Endpoint.INVOICES, params)


def fetch_customers() -> list:
    return fetch_all(Endpoint.CUSTOMERS)
