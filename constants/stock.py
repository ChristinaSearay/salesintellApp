"""View Products — the rep's window onto Unleashed stock.

The list is searched from the synced catalogue (data/view_products.json, as of
the last `uv run sync`); opening one product asks Unleashed live for its stock
in every warehouse. Searching Unleashed itself takes ~5s a page, too slow to
type against.
"""
from enum import Enum


class WarehouseGroup(Enum):
    """How a rep reads a warehouse: can I sell it, is it out at a shop, or neither."""
    OUR_STOCK = "Our stock"
    CONSIGNMENT = "At customers (consignment)"
    NOT_FOR_SALE = "Not for sale"
    # A warehouse added in Unleashed after this map was written. Shown under its
    # own heading rather than guessed into one of the others.
    UNSORTED = "Not yet sorted"


# Display order of the groups on a product page.
GROUP_ORDER = (WarehouseGroup.OUR_STOCK, WarehouseGroup.CONSIGNMENT,
               WarehouseGroup.NOT_FOR_SALE, WarehouseGroup.UNSORTED)

# Unleashed warehouse code -> group (the 12 warehouses as of 30 Oct 2026).
WAREHOUSE_GROUPS = {
    "WH": WarehouseGroup.OUR_STOCK,             # 1. Warehouse (default)
    "VIC": WarehouseGroup.OUR_STOCK,            # 2. VIC Bags
    "NSW": WarehouseGroup.OUR_STOCK,            # 3. NSW Bags
    "QLD": WarehouseGroup.OUR_STOCK,            # 4. QLD Bags
    "JF": WarehouseGroup.OUR_STOCK,             # 5. Jewellery Fairs
    "EJ403": WarehouseGroup.CONSIGNMENT,        # 6.1 Gama Jewellery
    "SCJ001": WarehouseGroup.CONSIGNMENT,       # 8. Simon Curwood Jewellers
    "PPJ898": WarehouseGroup.CONSIGNMENT,       # 9.1. Prime & Pure
    "LAV001": WarehouseGroup.CONSIGNMENT,       # 9.3 Lloyds
    "SSJ": WarehouseGroup.CONSIGNMENT,          # 10. Stephens Jewellers (S304)
    "RP": WarehouseGroup.NOT_FOR_SALE,          # 6. Repairs
    "UA": WarehouseGroup.NOT_FOR_SALE,          # 7. Unavailable
}

# One request per warehouse plus the product itself, all at once.
LIVE_STOCK_WORKERS = 16

# How long the engine trusts its copy of Unleashed's warehouse list, so a
# warehouse added in Unleashed shows up within the hour without a restart.
WAREHOUSE_LIST_TTL_SECONDS = 3600

# Products per page in the searchable list.
PRODUCT_PAGE_SIZE = 20

# GET /api/products?in_stock=1 -> only products with stock on hand.
IN_STOCK_ONLY = "1"
