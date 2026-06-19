"""Unleashed API configuration.

Credentials come from environment variables (NEVER commit them):
    UNLEASHED_API_ID    your API ID (a GUID)
    UNLEASHED_API_KEY   your API Key (the secret used to sign requests)

Find them in Unleashed → Integration → API Access. Then either:
    SEARAY_DATA_SOURCE=unleashed uv run sync     # pull into data/
    SEARAY_DATA_SOURCE=unleashed uv run dev       # run the app on live data
"""
import os

# Base URL + credentials (empty until the env vars are set).
API_URL = os.environ.get("UNLEASHED_API_URL", "https://api.unleashedsoftware.com")
API_ID = os.environ.get("UNLEASHED_API_ID", "")
API_KEY = os.environ.get("UNLEASHED_API_KEY", "")

PAGE_SIZE = 200          # Unleashed caps page size at 200
LOOKBACK_DAYS = 731      # ~24 months of orders/invoices to pull
RATE_LIMIT_PAUSE = 0.3   # seconds between page requests (be gentle)


# Endpoint paths under API_URL (verify names against the live API if they 404).
class Endpoint:
    PRODUCTS = "Products"
    STOCK_ON_HAND = "StockOnHand"
    SALES_ORDERS = "SalesOrders"
    INVOICES = "Invoices"
    CUSTOMERS = "Customers"


def has_credentials() -> bool:
    return bool(API_ID and API_KEY)
