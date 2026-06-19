"""Single source of truth for 'the current 3 actions for a customer'.

Used by BOTH the GUI server and report generation, so learned preferences feed
back into the one-page reports automatically. Loads the heavy data once and
caches it; per-customer preferences are read fresh each call so the latest
learning always applies.
"""
from typing import Dict, List, Optional

from constants.customers import TARGET_BY_CODE
from constants.recommended_actions import CUSTOMER_KIND
from utils.candidates import Candidate, build_candidate_pool
from utils.preferences import (
    apply_acceptance,
    apply_rejection,
    learned_chips,
    load_profile,
    rank_candidates,
    save_profile,
)
from utils.products import load_catalogue, load_product_master, make_resolver
from utils.profile import build_profiles

_CACHE: dict = {}


def _engine() -> dict:
    if not _CACHE:
        master = load_product_master()
        catalogue = load_catalogue(master)
        resolve = make_resolver(master, catalogue)
        profiles = {p.customer.code: p for p in build_profiles()}
        pools = {code: build_candidate_pool(p, catalogue, resolve)
                 for code, p in profiles.items()}
        _CACHE.update(resolve=resolve, profiles=profiles, pools=pools)
    return _CACHE


def _select_diverse(ranked: List[Candidate], n: int) -> List[Candidate]:
    """Top-n by score, but avoid showing two actions from the same primary
    group in one set. Falls back to fill if diversity can't reach n."""
    out, used_groups = [], set()
    for c in ranked:
        if len(out) >= n:
            break
        primary = c.groups[0] if c.groups else None
        if primary and primary in used_groups:
            continue
        out.append(c)
        if primary:
            used_groups.add(primary)
    if len(out) < n:
        for c in ranked:
            if len(out) >= n:
                break
            if c not in out:
                out.append(c)
    return out


def current_actions(code: str, n: int = 3) -> List[Candidate]:
    eng = _engine()
    profile = load_profile(code)
    ranked = rank_candidates(eng["pools"][code], profile)
    return _select_diverse(ranked, n)


# --- Serialisation for the web API -----------------------------------------

def candidate_to_json(c: Candidate) -> dict:
    resolve = _engine()["resolve"]
    products = []
    for p in c.pitches:
        desc, price, stock = resolve(p.code)
        products.append({
            "code": p.code, "desc": desc, "why": p.why,
            "price": price, "stock": stock,
        })
    return {
        "id": c.id,
        "title": c.title,
        "detail": c.detail,
        "kind": c.kind.value,
        "incentive": c.incentive,
        "incentive_type": c.incentive_type.value,
        "groups": list(c.groups),
        "products": products,
        "is_seed": c.is_seed,
    }


def customer_summary(code: str) -> dict:
    eng = _engine()
    p = eng["profiles"][code]
    profile = load_profile(code)
    flag = p.relationship.value
    return {
        "code": code,
        "name": p.customer.name,
        "segment": p.segment.value,
        "flag": flag,
        "flag_key": p.relationship.name,
        "rfm": p.rfm_code,
        "balance": p.customer.balance_owing,
        "kind": CUSTOMER_KIND.get(code, ""),
        "hooks": list(p.notes.hooks) if p.notes else [],
        "next_contact": (p.notes.next_contact if p.notes else "") or "",
        "snapshot": (f"{p.frequency} orders · ${p.monetary:,.0f} in 24 months · "
                     f"last order {p.recency_days} days ago"),
        "last_order_days": p.recency_days,
        "orders": p.frequency,
        "spend": p.monetary,
        "top_groups": [g.name for g in p.bought_groups[:4]],
        "learned": learned_chips(profile),
    }


def customer_list() -> List[dict]:
    return [customer_summary(code) for code in TARGET_BY_CODE]


def actions_payload(code: str, n: int = 3) -> dict:
    profile = load_profile(code)
    actions = [candidate_to_json(c) for c in current_actions(code, n)]
    for a in actions:
        a["accepted"] = a["id"] in profile.accepted_ids
    return {
        "customer": customer_summary(code),
        "actions": actions,
        "exhausted": len(actions) < n,
    }


# --- Applying feedback from the UI -----------------------------------------

def submit_feedback(code: str, accepted_ids: List[str], rejections: List[dict],
                    n: int = 3) -> dict:
    """rejections: [{id, reasons:[ReasonName], note}]. Persists, returns the
    refreshed action set."""
    from constants.feedback import RejectionReason  # local import avoids cycle at top
    eng = _engine()
    by_id = {c.id: c for c in eng["pools"][code]}
    profile = load_profile(code)

    for acc in accepted_ids or []:
        apply_acceptance(profile, acc)

    for rej in rejections or []:
        cand = by_id.get(rej.get("id"))
        if not cand:
            continue
        reasons = []
        for rname in rej.get("reasons", []):
            try:
                reasons.append(RejectionReason[rname])
            except KeyError:
                continue
        apply_rejection(profile, cand, reasons, rej.get("note", ""))

    save_profile(profile)
    return actions_payload(code, n)


def reset(code: str, n: int = 3) -> dict:
    from utils.preferences import reset_profile
    reset_profile(code)
    return actions_payload(code, n)
