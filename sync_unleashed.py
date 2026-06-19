"""Sync data from the Unleashed API into the local cache (data/).

Run:  uv run sync
Needs env vars:  UNLEASHED_API_ID, UNLEASHED_API_KEY
Then run the app on live data with:  SEARAY_DATA_SOURCE=unleashed uv run dev
"""
from utils.unleashed_sync import sync


def main() -> None:
    sync()


if __name__ == "__main__":
    main()
