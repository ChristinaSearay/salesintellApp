"""Per-customer learned preferences: persistence + the deterministic rules that
turn a rejection (reasons) into preference changes, and that score/rank
candidates given those preferences.

Saved as feedback/<code>.json so learning survives across sessions and can be
read by report generation too.
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from constants.config import FEEDBACK_DIR
from constants.feedback import (
    DISCOUNT_LIKE,
    PRICE_LOW_MAX,
    PRICE_MID_MAX,
    PUSHY_DEMOTE,
    PUSHY_PROMOTE,
    TIMING_DEMOTE,
    VARIETY_DEMOTE,
    ActionKind,
    IncentiveType,
    PriceBand,
    RejectionReason,
)

ACCEPTED_PIN = 1000.0  # keeps accepted actions on top


@dataclass
class PreferenceProfile:
    customer_code: str
    excluded_groups: set = field(default_factory=set)
    excluded_incentives: set = field(default_factory=set)   # IncentiveType names
    price_ceiling: Optional[str] = None                     # PriceBand name (max acceptable)
    kind_weights: Dict[str, float] = field(default_factory=dict)
    rejected_ids: set = field(default_factory=set)
    accepted_ids: set = field(default_factory=set)
    history: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    # --- (de)serialisation -------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "customer_code": self.customer_code,
            "excluded_groups": sorted(self.excluded_groups),
            "excluded_incentives": sorted(self.excluded_incentives),
            "price_ceiling": self.price_ceiling,
            "kind_weights": self.kind_weights,
            "rejected_ids": sorted(self.rejected_ids),
            "accepted_ids": sorted(self.accepted_ids),
            "history": self.history,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PreferenceProfile":
        return cls(
            customer_code=d["customer_code"],
            excluded_groups=set(d.get("excluded_groups", [])),
            excluded_incentives=set(d.get("excluded_incentives", [])),
            price_ceiling=d.get("price_ceiling"),
            kind_weights=dict(d.get("kind_weights", {})),
            rejected_ids=set(d.get("rejected_ids", [])),
            accepted_ids=set(d.get("accepted_ids", [])),
            history=list(d.get("history", [])),
            notes=list(d.get("notes", [])),
        )


def _path(code: str) -> str:
    return os.path.join(FEEDBACK_DIR, f"{code}.json")


def load_profile(code: str) -> PreferenceProfile:
    try:
        with open(_path(code), encoding="utf-8") as fh:
            return PreferenceProfile.from_dict(json.load(fh))
    except (FileNotFoundError, json.JSONDecodeError):
        return PreferenceProfile(customer_code=code)


def save_profile(profile: PreferenceProfile) -> None:
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    with open(_path(profile.customer_code), "w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2)


def reset_profile(code: str) -> PreferenceProfile:
    try:
        os.remove(_path(code))
    except FileNotFoundError:
        pass
    return PreferenceProfile(customer_code=code)


# --- Applying feedback (the learning) --------------------------------------

def _lower_ceiling(profile: PreferenceProfile, candidate) -> None:
    band = candidate.price_band
    # Nothing to do if the item has no price, or is already the cheapest tier
    # (rejecting a cheap item as "too expensive" shouldn't cap everything).
    if band is None or band.rank <= PriceBand.LOW.rank:
        return
    target_rank = band.rank - 1
    current = PriceBand[profile.price_ceiling].rank if profile.price_ceiling else None
    if current is None or target_rank < current:
        profile.price_ceiling = PriceBand(target_rank).name


def _scale_weight(profile: PreferenceProfile, kind: ActionKind, factor: float) -> None:
    cur = profile.kind_weights.get(kind.name, 1.0)
    profile.kind_weights[kind.name] = round(cur * factor, 3)


def _raise_weight(profile: PreferenceProfile, kind: ActionKind, floor: float) -> None:
    cur = profile.kind_weights.get(kind.name, 1.0)
    profile.kind_weights[kind.name] = max(cur, floor)


def apply_rejection(profile: PreferenceProfile, candidate, reasons: List[RejectionReason],
                    note: str = "") -> None:
    profile.rejected_ids.add(candidate.id)
    profile.accepted_ids.discard(candidate.id)
    for reason in reasons:
        if reason is RejectionReason.TOO_EXPENSIVE:
            _lower_ceiling(profile, candidate)
        elif reason in (RejectionReason.WRONG_PRODUCT, RejectionReason.ALREADY_HAVE):
            profile.excluded_groups.update(candidate.groups)
        elif reason is RejectionReason.NO_INCENTIVES:
            profile.excluded_incentives.update(t.name for t in DISCOUNT_LIKE)
            if candidate.incentive_type is not IncentiveType.NONE:
                profile.excluded_incentives.add(candidate.incentive_type.name)
        elif reason is RejectionReason.TOO_PUSHY:
            _scale_weight(profile, ActionKind.UPSELL, PUSHY_DEMOTE)
            _scale_weight(profile, ActionKind.WHITESPACE, PUSHY_DEMOTE)
            _raise_weight(profile, ActionKind.RELATIONSHIP, PUSHY_PROMOTE)
            _raise_weight(profile, ActionKind.RETENTION, 1.3)
        elif reason is RejectionReason.BAD_TIMING:
            _scale_weight(profile, candidate.kind, TIMING_DEMOTE)
        elif reason is RejectionReason.WANT_OTHER:
            _scale_weight(profile, candidate.kind, VARIETY_DEMOTE)
        # TRIED_BEFORE: the id exclusion above is the effect.
    profile.history.append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "candidate_id": candidate.id,
        "candidate_title": candidate.title,
        "reasons": [r.name for r in reasons],
        "note": note.strip(),
    })
    if note.strip():
        profile.notes.append(note.strip())


def apply_acceptance(profile: PreferenceProfile, candidate_id: str) -> None:
    profile.accepted_ids.add(candidate_id)
    profile.rejected_ids.discard(candidate_id)


# --- Scoring / ranking -----------------------------------------------------

def score_candidate(candidate, profile: PreferenceProfile) -> Optional[float]:
    """Return a score, or None if the candidate is filtered out entirely."""
    # Accepted actions are locked in: always shown, bypass every filter.
    if candidate.id in profile.accepted_ids:
        return candidate.base_score + ACCEPTED_PIN
    if candidate.id in profile.rejected_ids:
        return None
    if profile.excluded_groups.intersection(candidate.groups):
        return None
    if candidate.incentive_type.name in profile.excluded_incentives:
        return None
    if profile.price_ceiling and candidate.price_band is not None:
        if candidate.price_band.rank > PriceBand[profile.price_ceiling].rank:
            return None
    return candidate.base_score * profile.kind_weights.get(candidate.kind.name, 1.0)


def rank_candidates(pool, profile: PreferenceProfile):
    scored = [(c, score_candidate(c, profile)) for c in pool]
    scored = [(c, s) for c, s in scored if s is not None]
    scored.sort(key=lambda cs: -cs[1])
    return [c for c, _ in scored]


# --- UI helper: human-readable "what I've learned" -------------------------

def learned_chips(profile: PreferenceProfile) -> List[dict]:
    chips = []
    if profile.price_ceiling:
        cap = PRICE_LOW_MAX if profile.price_ceiling == PriceBand.LOW.name else PRICE_MID_MAX
        chips.append({"icon": "💲", "label": f"Keep under ${cap:,.0f}"})
    for g in sorted(profile.excluded_groups):
        chips.append({"icon": "🚫", "label": f"No {g}"})
    if profile.excluded_incentives & {t.name for t in DISCOUNT_LIKE}:
        chips.append({"icon": "🏷️", "label": "No discounts"})
    if profile.kind_weights.get(ActionKind.RELATIONSHIP.name, 1.0) > 1.0:
        chips.append({"icon": "🤝", "label": "Low-pressure first"})
    return chips
