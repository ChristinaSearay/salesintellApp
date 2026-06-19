"""Step 4 — generate the five one-page Markdown sales action reports.

Run:  python3 build_reports.py
Writes reports/<code> - <name>.md and prints a summary.
"""
import os
import re

from constants.config import REPORTS_DIR
from constants.recommended_actions import RECOMMENDED_ACTIONS
from utils.products import load_catalogue, load_product_master
from utils.profile import build_profiles
from utils.report import render


def make_resolver(master, catalogue):
    """code -> (description, price, stock_label|None). Catalogue (with live
    stock) takes priority; master is the fallback for items not in View
    Products (e.g. the testing machines)."""
    cat_by_code = {i.code: i for i in catalogue}

    def resolve(code):
        item = cat_by_code.get(code)
        if item:
            return (item.description, item.sell_price, item.stock_status.value)
        m = master.get(code)
        if m:
            return (m.description, m.sell_price, None)
        return (code, None, None)

    return resolve


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w\- ]", "", name).strip()


def main() -> None:
    master = load_product_master()
    catalogue = load_catalogue(master)
    resolve = make_resolver(master, catalogue)
    profiles = build_profiles()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    written = []
    for p in profiles:
        actions = RECOMMENDED_ACTIONS.get(p.customer.code, ())
        md = render(p, actions, resolve)
        fname = f"{p.customer.code} - {_safe_name(p.customer.name)}.md"
        path = os.path.join(REPORTS_DIR, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(md + "\n")
        written.append((fname, len(actions), len(md)))

    print("Wrote reports:")
    for fname, n_actions, size in written:
        print(f"   reports/{fname}   ({n_actions} actions, {size:,} chars)")


if __name__ == "__main__":
    main()
