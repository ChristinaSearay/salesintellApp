"""Live customer intel store: summarised WhatsApp updates per customer.

Persisted as notes/<code>.json (a list of IntelUpdate dicts, oldest first).
`effective_context(code)` layers the updates over the static MEETING_NOTES
baseline and returns a MeetingContext — the same shape the profile, the
candidate pool and the report renderer already consume. Read fresh on every
call (like feedback/), so a saved update shows up in the GUI immediately.
"""
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from constants.config import NOTES_DIR
from constants.intel import MAX_LIVE_HOOKS, MAX_TOTAL_HOOKS, UNCHANGED, IntelSource
from constants.meeting_notes import MEETING_NOTES, MeetingContext
from constants.products import canonical_group
from constants.rfm import RelationshipFlag


@dataclass
class IntelUpdate:
    customer_code: str
    hooks: List[str]
    source: str = IntelSource.WHATSAPP.value
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    raw_text: str = ""
    customer_as_written: str = ""
    opportunity_groups: List[str] = field(default_factory=list)
    referenced_products: List[str] = field(default_factory=list)
    prior_incentive: str = ""
    relationship: str = UNCHANGED   # RelationshipFlag name or UNCHANGED
    next_contact: str = ""
    advice: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "IntelUpdate":
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)

    @property
    def relationship_flag(self) -> Optional[RelationshipFlag]:
        if self.relationship == UNCHANGED:
            return None
        try:
            return RelationshipFlag[self.relationship]
        except KeyError:
            return None


# --- persistence -----------------------------------------------------------

def _path(code: str) -> str:
    return os.path.join(NOTES_DIR, f"{code}.json")


def load_updates(code: str) -> List[IntelUpdate]:
    try:
        with open(_path(code), encoding="utf-8") as fh:
            return [IntelUpdate.from_dict(d) for d in json.load(fh)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(code: str, updates: List[IntelUpdate]) -> None:
    os.makedirs(NOTES_DIR, exist_ok=True)
    with open(_path(code), "w", encoding="utf-8") as fh:
        json.dump([u.to_dict() for u in updates], fh, indent=2)


def add_update(update: IntelUpdate) -> IntelUpdate:
    update.hooks = [h.strip() for h in update.hooks if h and h.strip()]
    update.opportunity_groups = [canonical_group(g) for g in update.opportunity_groups]
    updates = load_updates(update.customer_code)
    updates.append(update)
    _save(update.customer_code, updates)
    return update


def add_note(code: str, text: str) -> IntelUpdate:
    """A rep's own note (what is / isn't working) — shown in "What's going on"."""
    text = text.strip()
    return add_update(IntelUpdate(customer_code=code, hooks=[text],
                                  source=IntelSource.MANUAL.value, raw_text=text))


def latest_updates() -> Dict[str, IntelUpdate]:
    """code -> newest saved update, for every customer that has one (one
    directory scan, so the attention queue doesn't open a file per customer)."""
    try:
        names = os.listdir(NOTES_DIR)
    except FileNotFoundError:
        return {}
    out: Dict[str, IntelUpdate] = {}
    for name in names:
        code, ext = os.path.splitext(name)
        if ext == ".json":
            latest = latest_update(code)
            if latest:
                out[code] = latest
    return out


def delete_update(code: str, update_id: str) -> bool:
    updates = load_updates(code)
    kept = [u for u in updates if u.id != update_id]
    if len(kept) == len(updates):
        return False
    _save(code, kept)
    return True


def clear_updates(code: str) -> None:
    try:
        os.remove(_path(code))
    except FileNotFoundError:
        pass


# --- merge over the meeting-notes baseline ---------------------------------

def effective_context(code: str) -> Optional[MeetingContext]:
    """Baseline MEETING_NOTES + live updates, newest update wins for the
    single-valued fields; hooks and groups accumulate."""
    base = MEETING_NOTES.get(code)
    updates = load_updates(code)
    if not updates:
        return base

    newest_first = list(reversed(updates))
    live_hooks: List[str] = []
    for u in newest_first:
        for h in u.hooks:
            if len(live_hooks) >= MAX_LIVE_HOOKS:
                break
            if h not in live_hooks:
                live_hooks.append(h)
    base_hooks = list(base.hooks) if base else []
    hooks = (live_hooks + [h for h in base_hooks if h not in live_hooks])[:MAX_TOTAL_HOOKS]

    groups: List[str] = []
    for u in newest_first:
        for g in u.opportunity_groups:
            if g not in groups:
                groups.append(g)
    for g in (base.opportunity_groups if base else ()):
        if g not in groups:
            groups.append(g)

    products: List[str] = []
    for u in newest_first:
        for p in u.referenced_products:
            if p not in products:
                products.append(p)
    for p in (base.referenced_products if base else ()):
        if p not in products:
            products.append(p)

    relationship = next((u.relationship_flag for u in newest_first if u.relationship_flag), None) \
        or (base.relationship if base else RelationshipFlag.NONE)
    prior_incentive = next((u.prior_incentive for u in newest_first if u.prior_incentive), "") \
        or (base.prior_incentive if base else "")
    next_contact = next((u.next_contact for u in newest_first if u.next_contact), "") \
        or (base.next_contact if base else "")

    latest = newest_first[0]
    narrative = (base.narrative if base else "")
    if latest.hooks:
        narrative = (f"{narrative}\n\nLatest update ({latest.ts[:10]}, {latest.source}): "
                     + " ".join(latest.hooks)).strip()

    return MeetingContext(
        narrative=narrative,
        relationship=relationship,
        opportunity_groups=tuple(groups),
        referenced_products=tuple(products),
        prior_incentive=prior_incentive,
        hooks=tuple(hooks),
        next_contact=next_contact,
    )


def live_hook_set(code: str) -> set:
    """Hooks that came from live updates (so the UI can tag them)."""
    return {h for u in load_updates(code) for h in u.hooks}


def latest_update(code: str) -> Optional[IntelUpdate]:
    updates = load_updates(code)
    return updates[-1] if updates else None
