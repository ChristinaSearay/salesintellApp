"""Turn a business we visited into a real Unleashed customer.

Read the flow as three steps, mirroring Christina's:
  check(name)   -> is this actually new, or do we already have them?
  suggest_code  -> a code in the same shape as the existing ones
  create(...)   -> write it to Unleashed, so a later order syncs straight in

Nothing here is automatic: the rep sees the near-duplicates and confirms.
"""
import difflib
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from constants.prospects import (
    CODE_FALLBACK_LETTERS,
    CODE_FIRST_NUMBER,
    CODE_MAX_LETTERS,
    CODE_MAX_NUMBER,
    DUPLICATE_RATIO,
    MAX_DUPLICATE_SUGGESTIONS,
    MAX_NAME_LENGTH,
    MIN_NAME_LENGTH,
    NAME_CONTAINMENT_IS_DUPLICATE,
    MIN_CONTAINMENT_WORDS,
    NAME_NOISE,
    ProspectField,
    ProspectOutcome,
)
from constants.columns import CustomerCol
from constants.unleashed import Endpoint
from utils import unleashed as api
from utils.customers import load_customers
from utils.datasource import customer_rows
from utils.prospect_store import load_all as load_prospects, save as save_prospect


@dataclass(frozen=True)
class Match:
    code: str
    name: str
    score: float


@dataclass(frozen=True)
class ProspectCheck:
    outcome: ProspectOutcome
    name: str
    suggested_code: str
    matches: List[Match]


def _words(name: str) -> List[str]:
    """Lowercase significant words: punctuation and legal form removed."""
    lowered = (name or "").lower().replace("'", "").replace("’", "")
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    return [w for w in cleaned.split() if w and w not in NAME_NOISE]


def directory() -> Dict[str, str]:
    """code -> name for EVERY customer Unleashed holds, not just the ones who
    have ordered. The whole point here is businesses with no order history, so
    checking only active customers would happily create a second Gama Gold."""
    known = {row_code: row_name for row_code, row_name in (
        ((r.get(CustomerCol.CODE) or "").strip(), (r.get(CustomerCol.NAME) or "").strip())
        for r in customer_rows()
    ) if row_code}
    # Prospects created since the last sync aren't in the cache yet — without
    # them we'd happily offer to create the same shop again an hour later.
    for code, record in load_prospects().items():
        known.setdefault(code, (record.get("name") or "").strip())
    # CSV mode has no customer master; fall back to whoever has traded.
    for code, customer in load_customers().items():
        known.setdefault(code, customer.name)
    return known


def normalise_name(name: str) -> str:
    return " ".join(_words(name))


def validate_name(name: str) -> str:
    """Return the trimmed name, or raise ValueError with a rep-readable reason."""
    trimmed = (name or "").strip()
    if len(trimmed) < MIN_NAME_LENGTH:
        raise ValueError(f"Business name must be at least {MIN_NAME_LENGTH} characters.")
    if len(trimmed) > MAX_NAME_LENGTH:
        raise ValueError(f"Business name must be under {MAX_NAME_LENGTH} characters.")
    if not normalise_name(trimmed):
        raise ValueError("That name is only punctuation or filler words.")
    return trimmed


def find_matches(name: str, known: Optional[Dict[str, str]] = None) -> List[Match]:
    """Existing customers that could be this business, best first."""
    target = normalise_name(name)
    if not target:
        return []
    known = directory() if known is None else known

    scored = []
    for code, customer_name in known.items():
        other = normalise_name(customer_name)
        if not other:
            continue
        if other == target:
            scored.append(Match(code, customer_name, 1.0))
            continue
        ratio = difflib.SequenceMatcher(None, target, other).ratio()
        # "temple of the sun" vs "temple of the sun jewellery": a short name
        # sitting wholly inside a longer one scores low but is the same shop.
        contained = target in other or other in target
        substantial = min(len(target.split()), len(other.split())) >= MIN_CONTAINMENT_WORDS
        if NAME_CONTAINMENT_IS_DUPLICATE and contained and substantial:
            ratio = max(ratio, DUPLICATE_RATIO)
        if ratio >= DUPLICATE_RATIO:
            scored.append(Match(code, customer_name, round(ratio, 3)))

    scored.sort(key=lambda m: (-m.score, m.name))
    return scored[:MAX_DUPLICATE_SUGGESTIONS]


def suggest_code(name: str, known: Optional[Dict[str, str]] = None) -> str:
    """A free code shaped like the ones Unleashed already holds (EJ403, MJ001)."""
    known = directory() if known is None else known
    taken = {c.upper() for c in known}

    words = _words(name)
    letters = "".join(w[0] for w in words[:CODE_MAX_LETTERS]).upper()
    if not letters:
        letters = CODE_FALLBACK_LETTERS

    for n in range(CODE_FIRST_NUMBER, CODE_MAX_NUMBER + 1):
        candidate = f"{letters}{n:03d}"
        if candidate not in taken:
            return candidate
    raise RuntimeError(f"No free customer code left for '{letters}'.")


def check(name: str, known: Optional[Dict[str, str]] = None) -> ProspectCheck:
    """Is this business new? Never writes anything."""
    clean = validate_name(name)
    known = directory() if known is None else known
    matches = find_matches(clean, known)

    if matches and matches[0].score >= 1.0:
        outcome = ProspectOutcome.EXISTS
    elif matches:
        outcome = ProspectOutcome.POSSIBLE_DUPLICATE
    else:
        outcome = ProspectOutcome.NEW

    return ProspectCheck(
        outcome=outcome,
        name=clean,
        suggested_code=suggest_code(clean, known),
        matches=matches,
    )


def build_payload(name: str, code: str, contact_name: str = "", phone: str = "",
                  email: str = "") -> dict:
    """The bare-minimum Unleashed Customer object."""
    first, _, last = (contact_name or "").strip().partition(" ")
    payload = {
        ProspectField.GUID: str(uuid.uuid4()),
        ProspectField.CODE: code,
        ProspectField.NAME: name,
    }
    if first:
        payload[ProspectField.CONTACT_FIRST] = first
    if last.strip():
        payload[ProspectField.CONTACT_LAST] = last.strip()
    if email.strip():
        payload[ProspectField.EMAIL] = email.strip()
    if phone.strip():
        payload[ProspectField.MOBILE] = phone.strip()
    return payload


def create(name: str, code: str = "", contact_name: str = "", phone: str = "",
           email: str = "", dry_run: bool = False) -> dict:
    """Create the customer in Unleashed and return {code, name, guid, created}.

    dry_run returns exactly what would be sent without calling Unleashed.
    """
    clean = validate_name(name)
    known = directory()
    chosen = (code or "").strip().upper() or suggest_code(clean, known)
    if chosen in {c.upper() for c in known}:
        raise ValueError(f"Customer code {chosen} is already used.")

    payload = build_payload(clean, chosen, contact_name, phone, email)
    if dry_run:
        return {"code": chosen, "name": clean, "guid": payload[ProspectField.GUID],
                "created": False, "payload": payload}

    api.post(Endpoint.CUSTOMERS, payload[ProspectField.GUID], payload)
    # Remember it locally: the sync cache won't hold it until the next
    # `uv run sync`, and the rep needs the customer to exist in the app now.
    save_prospect(chosen, clean, payload[ProspectField.GUID],
                  contact_name=contact_name, phone=phone, email=email)
    load_customers.cache_clear()
    return {"code": chosen, "name": clean, "guid": payload[ProspectField.GUID],
            "created": True}
