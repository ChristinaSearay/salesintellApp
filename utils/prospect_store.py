"""Local record of customers we created in Unleashed from a visit.

Deliberately dependency-free (no utils.customers) so the directory can read it
without a circular import. One small JSON file per customer code, like notes/,
so it lives happily on the same persistent disk.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict

from constants.config import PROSPECTS_DIR


def _path(code: str) -> str:
    return os.path.join(PROSPECTS_DIR, f"{code}.json")


def save(code: str, name: str, guid: str = "", **extra) -> dict:
    os.makedirs(PROSPECTS_DIR, exist_ok=True)
    record = {
        "code": code,
        "name": name,
        "guid": guid,
        "created_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        **{k: v for k, v in extra.items() if v},
    }
    with open(_path(code), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    return record


def load_all() -> Dict[str, dict]:
    """code -> record. Read fresh every call, like notes."""
    try:
        files = os.listdir(PROSPECTS_DIR)
    except FileNotFoundError:
        return {}
    out: Dict[str, dict] = {}
    for filename in files:
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(PROSPECTS_DIR, filename), encoding="utf-8") as fh:
                record = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue  # a half-written file must not take the directory down
        code = (record.get("code") or "").strip()
        if code:
            out[code] = record
    return out
