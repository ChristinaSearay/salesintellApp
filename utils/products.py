"""Product master + new-product catalogue, and the matching helpers that power
the upsell engine.

File 2 (View Products) has the Created On date and live stock but NO product
group, so every catalogue item is joined to File 1 (Products) on product code to
pick up its canonical Product Group.
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from constants.columns import ProductCol, ViewCol
from constants.config import PRODUCTS_FILE, VIEW_PRODUCTS_FILE
from constants.products import (
    EXCLUDED_GROUPS,
    EXCLUDED_PRODUCT_CODES,
    ON_HAND_IN_STOCK_MIN,
    StockStatus,
    canonical_group,
)
from utils.dataio import load_table
from utils.parsing import parse_date, parse_money, parse_number


@dataclass(frozen=True)
class MasterProduct:
    code: str
    description: str
    group: str          # canonical Product Group
    sell_price: float


@dataclass(frozen=True)
class CatalogueItem:
    """A product from View Products, enriched with its master Product Group."""
    code: str
    description: str
    group: str
    created_on: Optional[date]
    sell_price: float
    on_hand: float
    available: float

    @property
    def stock_status(self) -> StockStatus:
        return (StockStatus.IN_STOCK if self.on_hand > ON_HAND_IN_STOCK_MIN
                else StockStatus.BACKORDER)

    @property
    def in_stock(self) -> bool:
        return self.stock_status is StockStatus.IN_STOCK


def load_product_master() -> Dict[str, MasterProduct]:
    """code -> MasterProduct (canonical group) from File 1."""
    master: Dict[str, MasterProduct] = {}
    for row in load_table(PRODUCTS_FILE):
        code = (row.get(ProductCol.CODE) or "").strip()
        if not code:
            continue
        master[code] = MasterProduct(
            code=code,
            description=(row.get(ProductCol.DESCRIPTION) or "").strip(),
            group=canonical_group(row.get(ProductCol.GROUP)),
            sell_price=parse_money(row.get(ProductCol.SELL_PRICE)),
        )
    return master


def load_catalogue(master: Dict[str, MasterProduct]) -> List[CatalogueItem]:
    """All View Products rows as CatalogueItems, group joined from the master."""
    catalogue: List[CatalogueItem] = []
    for row in load_table(VIEW_PRODUCTS_FILE):
        code = (row.get(ViewCol.CODE) or "").strip()
        if not code or code in EXCLUDED_PRODUCT_CODES:
            continue
        m = master.get(code)
        group = m.group if m else ""
        # Prefer the View price; fall back to master.
        price = parse_money(row.get(ViewCol.SELL_PRICE)) or (m.sell_price if m else 0.0)
        catalogue.append(CatalogueItem(
            code=code,
            description=(row.get(ViewCol.DESCRIPTION) or "").strip(),
            group=group,
            created_on=parse_date(row.get(ViewCol.CREATED_ON)),
            sell_price=price,
            on_hand=parse_number(row.get(ViewCol.ON_HAND)),
            available=parse_number(row.get(ViewCol.AVAILABLE)),
        ))
    return catalogue


# --- Matching helpers ------------------------------------------------------

def is_pitchable(item: CatalogueItem) -> bool:
    """A catalogue item we can actually merchandise (real group, not excluded)."""
    return bool(item.group) and item.group not in EXCLUDED_GROUPS


def new_since(catalogue: List[CatalogueItem], cutoff: Optional[date]) -> List[CatalogueItem]:
    """Items created strictly after `cutoff` (the customer's last order date)."""
    if cutoff is None:
        return [i for i in catalogue if is_pitchable(i)]
    return [i for i in catalogue
            if is_pitchable(i) and i.created_on is not None and i.created_on > cutoff]


def rank_items(items: List[CatalogueItem]) -> List[CatalogueItem]:
    """In-stock first, then by newest, then by value."""
    return sorted(
        items,
        key=lambda i: (
            not i.in_stock,
            -(i.created_on.toordinal() if i.created_on else 0),
            -i.sell_price,
        ),
    )


def newest_in_groups(catalogue: List[CatalogueItem], groups, limit: int = 5,
                     in_stock_only: bool = False) -> List[CatalogueItem]:
    """Newest catalogue items within a set of groups (e.g. meeting-notes hooks),
    regardless of the customer's last-order date. Used as a fallback when the
    'new since last order' window is empty (very recent customers)."""
    wanted = {canonical_group(g) for g in groups}
    items = [i for i in catalogue
             if i.group in wanted and is_pitchable(i)
             and (i.in_stock or not in_stock_only)]
    return rank_items(items)[:limit]
