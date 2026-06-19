"""The engine's data source — CSV exports (default) or the Unleashed sync cache.

Both paths return column-keyed rows (matching constants/columns.py), so the
loaders don't care where the data came from. Selected by SEARAY_DATA_SOURCE.
"""
import json
import os

from constants.config import (
    CACHE_DIR,
    DATA_SOURCE,
    INVOICE_FILE,
    PRODUCTS_FILE,
    SALES_FILE,
    VIEW_PRODUCTS_FILE,
    DataSource,
)
from utils.dataio import load_table

_using_unleashed = DATA_SOURCE == DataSource.UNLEASHED


def _cache(name: str) -> list:
    path = os.path.join(CACHE_DIR, name)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"SEARAY_DATA_SOURCE=unleashed but {path} is missing — run `uv run sync` first."
        ) from exc


def _rows(cache_name: str, file_spec) -> list:
    return _cache(cache_name) if _using_unleashed else load_table(file_spec)


def products_rows() -> list:
    return _rows("products.json", PRODUCTS_FILE)


def view_products_rows() -> list:
    return _rows("view_products.json", VIEW_PRODUCTS_FILE)


def sales_rows() -> list:
    return _rows("sales.json", SALES_FILE)


def invoice_rows() -> list:
    return _rows("invoices.json", INVOICE_FILE)
