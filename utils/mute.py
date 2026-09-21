"""Accounts a rep told us to stop reminding them about.

Christina's rule: "save note — do not alert again" takes the account out of the
needs-attention queue and keeps it out UNTIL an order is placed on it, at which
point alerting reverts to normal. Nothing expires on a timer — this is a mute,
not the 30-day snooze a plain note gives you.

So a mute stores the account's last order date at the moment it was set. It
holds while that is still their latest order and lifts by itself the moment a
newer one lands in the sync — `active()` clears the file then, so the account
is genuinely back to normal rather than muted-but-ignored. (Reps run two
accounts for the same shop: a buying-group one they rarely use and an
independent one they always use. The quiet one is noise until it isn't.)

Stored under the notes directory (mutes/<code>.json) so the deployed persistent
disk covers it with no extra configuration. Dependency-free on purpose — both
the attention queue and the recommender read it.
"""
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Dict, Optional

from constants.attention import NO_ORDER_MARK
from constants.config import MUTES_DIR


@dataclass(frozen=True)
class Mute:
    code: str
    ts: str
    order_mark: str          # their last order date when muted; NO_ORDER_MARK if they'd never ordered
    note: str = ""           # why the rep muted them, in their words

    def lifted_by(self, last_order: Optional[date]) -> bool:
        """True once an order newer than the watermark has landed."""
        if last_order is None:
            return False
        if self.order_mark == NO_ORDER_MARK:
            return True
        return last_order.isoformat() > self.order_mark   # ISO dates sort as text


def _path(code: str) -> str:
    return os.path.join(MUTES_DIR, f"{code}.json")


def get(code: str) -> Optional[Mute]:
    try:
        with open(_path(code), encoding="utf-8") as fh:
            d = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    known = {k: d[k] for k in Mute.__dataclass_fields__ if k in d}
    return Mute(**known)


def load_all() -> Dict[str, Mute]:
    """code -> Mute for every muted account (one directory scan, so the queue
    doesn't stat a file per customer)."""
    try:
        names = os.listdir(MUTES_DIR)
    except FileNotFoundError:
        return {}
    out: Dict[str, Mute] = {}
    for name in names:
        code, ext = os.path.splitext(name)
        if ext == ".json":
            m = get(code)
            if m:
                out[code] = m
    return out


def save(code: str, last_order: Optional[date], note: str = "") -> Mute:
    m = Mute(
        code=code,
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        order_mark=last_order.isoformat() if last_order else NO_ORDER_MARK,
        note=note.strip(),
    )
    os.makedirs(MUTES_DIR, exist_ok=True)
    with open(_path(code), "w", encoding="utf-8") as fh:
        json.dump(asdict(m), fh, indent=2)
    return m


def remove(code: str) -> bool:
    try:
        os.remove(_path(code))
        return True
    except FileNotFoundError:
        return False


def active(code: str, last_order: Optional[date]) -> Optional[Mute]:
    """The mute in force on this account, or None — clearing it if they've
    ordered since."""
    m = get(code)
    if m and m.lifted_by(last_order):
        remove(code)
        return None
    return m
