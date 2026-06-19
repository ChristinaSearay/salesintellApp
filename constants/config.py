"""Global configuration: anchor date, paths, and per-file read specs.

The four Unleashed exports are NOT uniformly encoded and two carry a title
row above the real header, so each file gets an explicit FileSpec rather than
being read with one set of assumptions.
"""
import os
from dataclasses import dataclass
from datetime import date

# All four exports are dated "as of 17/06/2026"; recency is measured from this
# snapshot, not the wall-clock date. (Confirmed with business owner.)
ANCHOR_DATE = date(2026, 6, 17)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Example Data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# 24-month lookback window for RFM (informational; the exports are already
# scoped to ~2 years by Unleashed).
LOOKBACK_MONTHS = 24


@dataclass(frozen=True)
class FileSpec:
    """One source CSV: its name, true encoding, and the 0-based index of the
    header row (rows above the header are title banners to skip)."""
    filename: str
    encoding: str
    header_row: int

    @property
    def path(self) -> str:
        return os.path.join(DATA_DIR, self.filename)


# File 1 is UTF-8 *with BOM* (utf-8-sig strips it); files 3 & 4 contain bytes
# that are not valid UTF-8, so they are genuinely latin-1. File 2 is clean UTF-8.
PRODUCTS_FILE = FileSpec("1. Products Export - 17.6.26.csv", "utf-8-sig", 0)
VIEW_PRODUCTS_FILE = FileSpec("2. View Products Export - 17.6.26.csv", "utf-8", 1)
SALES_FILE = FileSpec("3. Sales Enquiry Export - 17.6.26.csv", "latin-1", 1)
INVOICE_FILE = FileSpec("4. Invoice Enquiry Export - 17.6.26.csv", "latin-1", 1)
