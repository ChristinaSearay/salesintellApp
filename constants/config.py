"""Global configuration: anchor date, paths, and per-file read specs.

The four Unleashed exports are NOT uniformly encoded and two carry a title
row above the real header, so each file gets an explicit FileSpec rather than
being read with one set of assumptions.
"""
import os
from dataclasses import dataclass
from datetime import date

# Where the engine reads its data from.
class DataSource:
    CSV = "csv"            # manual Unleashed exports in Example Data/
    UNLEASHED = "unleashed"  # live sync cache in data/ (written by `uv run sync`)


# Chosen by env var; live Unleashed data is the default since 04 Sep 2026.
# SEARAY_DATA_SOURCE=csv returns to the committed snapshot exports.
DATA_SOURCE = os.environ.get("SEARAY_DATA_SOURCE", DataSource.UNLEASHED)

# Recency is measured from the data's snapshot date. Live Unleashed data is
# current, so the anchor is today; the CSV exports are dated "as of 17/06/2026",
# so CSV mode keeps that fixed anchor (confirmed with business owner) — which
# also keeps the CSV regression numbers stable.
CSV_SNAPSHOT_DATE = date(2026, 6, 17)


def anchor_date() -> date:
    """Today in live mode, the export snapshot in CSV mode.

    A function, not a constant: the server is long-running, and a module-level
    date.today() froze the anchor at process start — "days since last order"
    silently stopped advancing until the next deploy. Callers must read it per
    request; utils.recommend rebuilds its engine cache when this changes.
    """
    return date.today() if DATA_SOURCE == DataSource.UNLEASHED else CSV_SNAPSHOT_DATE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Example Data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
# Per-customer learned preferences (rejection -> re-suggestion loop) live here.
# Override with SEARAY_FEEDBACK_DIR to point at a persistent disk (e.g. on Render).
FEEDBACK_DIR = os.environ.get("SEARAY_FEEDBACK_DIR") or os.path.join(BASE_DIR, "feedback")
# Ideas the reps wrote themselves, reused across similar customers. A
# sub-directory of the feedback dir (which is only ever read by customer code,
# never scanned) so the deployed persistent disk covers it without another env var.
PLAYBOOK_DIR = os.path.join(FEEDBACK_DIR, "playbook")
# Per-customer live intel (summarised WhatsApp updates) layered over meeting notes.
NOTES_DIR = os.environ.get("SEARAY_NOTES_DIR") or os.path.join(BASE_DIR, "notes")
# Accounts a rep asked us to stop reminding them about ("do not alert again").
# A sub-directory of the notes dir so the deployed persistent disk covers it
# without another env var; the ".json" scan in utils/intel.py skips directories.
MUTES_DIR = os.path.join(NOTES_DIR, "mutes")
# Businesses the reps created in Unleashed from a visit. Kept locally too, so
# they show up in the app straight away instead of only after the next sync
# (and so we don't offer to create the same shop twice the same day).
PROSPECTS_DIR = os.environ.get("SEARAY_PROSPECTS_DIR") or os.path.join(BASE_DIR, "prospects")

# 24-month lookback window for RFM (informational; the exports are already
# scoped to ~2 years by Unleashed).
LOOKBACK_MONTHS = 24

# Rep web app (server.py / uv run app)
DEFAULT_PORT = 8000


CACHE_DIR = os.path.join(BASE_DIR, "data")  # Unleashed sync cache (committed, like Example Data/)


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
