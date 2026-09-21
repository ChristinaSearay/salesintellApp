"""Single source of truth for 'the current 3 actions for a customer'.

Used by BOTH the GUI server and report generation, so learned preferences feed
back into the one-page reports automatically. Loads the heavy data once and
caches it; per-customer preferences are read fresh each call so the latest
learning always applies.
"""
from typing import Dict, List, Optional

from constants.config import anchor_date
from constants.feedback import ActionKind, IncentiveType
from constants.intel import (
    LIVE_CHURN_RETENTION_BOOST,
    LIVE_CHURN_SELL_DEMOTE,
    LIVE_OPPORTUNITY_BONUS,
)
from constants.playbook import IDEA_BASE_SCORE, IDEA_ID_MARKER, IdeaOrigin
from constants.recommended_actions import CUSTOMER_KIND
from constants.rfm import RelationshipFlag
from utils.candidates import Candidate, build_candidate_pool, opportunity_candidates
from utils import mute, playbook
from utils.intel import effective_context, latest_update, live_hook_set, load_updates
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
    # Keyed on the anchor date: profiles bake in recency and RFM scores, so a
    # long-running server must rebuild them when the day rolls over, or every
    # "days since last order" stays frozen at whenever the process started.
    today = anchor_date()
    if not _CACHE or _CACHE.get("anchor") != today:
        _CACHE.clear()
        master = load_product_master()
        catalogue = load_catalogue(master)
        resolve = make_resolver(master, catalogue)
        profiles = {p.customer.code: p for p in build_profiles()}
        pools = {code: build_candidate_pool(p, catalogue, resolve)
                 for code, p in profiles.items()}
        groups = sorted({i.group for i in catalogue if i.group})
        _CACHE.update(resolve=resolve, profiles=profiles, pools=pools,
                      catalogue=catalogue, groups=groups, anchor=today)
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


# --- Live intel (WhatsApp) layered over the cached pool ---------------------

def _live_candidates(code: str) -> List[Candidate]:
    """Extra candidates derived from saved WhatsApp updates: new opportunity
    groups the baseline pool doesn't cover, and a 'respond to the terms they
    asked for' action when an incentive was raised. Computed per request so a
    freshly saved update changes the pitch set without a restart."""
    updates = load_updates(code)
    if not updates:
        return []
    eng = _engine()
    prof = eng["profiles"][code]
    pool = eng["pools"][code]
    covered = {g for c in pool for g in c.groups}
    used = {p.code for c in pool for p in c.pitches}
    latest = updates[-1]

    groups, why = [], ""
    for u in reversed(updates):
        for g in u.opportunity_groups:
            if g not in covered and g not in groups:
                groups.append(g)
        if not why and u.hooks:
            why = "From WhatsApp: " + u.hooks[0]
    out = opportunity_candidates(code, eng["catalogue"], groups, used, prof.bought_group_names,
                                 bonus=LIVE_OPPORTUNITY_BONUS, why=why)

    if latest.prior_incentive:
        out.append(Candidate(
            id=f"{code}-live-terms-{latest.id}",
            title="Respond to the terms they asked for",
            detail=(f"They raised: {latest.prior_incentive}. Come with a position on it — "
                    "a counter or a clear reason — rather than leaving it hanging."
                    + (f" {latest.advice}" if latest.advice else "")),
            kind=ActionKind.STRUCTURAL,
            incentive_type=IncentiveType.PRICE_MATCH,
            base_score=80.0,
            incentive=f"PROPOSED: {latest.prior_incentive}",
            grounded_in=f"WhatsApp update {latest.ts[:10]}.",
        ))
    return out


def _idea_candidates(code: str) -> List[Candidate]:
    """The rep playbook (utils/playbook.py): what a rep pitched here themselves,
    plus ideas they wrote on customers in the same situation. Computed per
    request, like live intel, so an idea saved on one visit is in play on the
    next one without a restart."""
    profile = _engine()["profiles"][code]
    out = []
    for idea, origin in playbook.for_customer(profile):
        own = origin is IdeaOrigin.OWN
        out.append(Candidate(
            id=f"{code}{IDEA_ID_MARKER}{idea.id}",
            title=idea.title,
            detail=idea.detail,
            kind=ActionKind.REP_IDEA,
            incentive_type=IncentiveType.NONE,
            # Confidence is global: an idea other reps took up outranks a fresh one.
            base_score=IDEA_BASE_SCORE * (1.0 if own else idea.confidence),
            groups=idea.groups,
            grounded_in=f"Rep idea recorded on {idea.origin_name} ({idea.when}).",
            origin=("Your idea, recorded " + idea.when if own
                    else f"Your idea from {idea.origin_name} — same situation"),
        ))
    return out


def _live_pool(code: str) -> List[Candidate]:
    return _engine()["pools"][code] + _live_candidates(code) + _idea_candidates(code)


def record_idea(code: str, title: str, detail: str = "", n: int = 3) -> dict:
    """The rep pitched something of their own. Save it and re-rank."""
    playbook.record(_engine()["profiles"][code], title, detail)
    return actions_payload(code, n)


def _tilt_for_relationship(code: str, profile):
    """Transient kind-weight tilt when the latest live update flags churn —
    not persisted, so it lifts as soon as the intel changes."""
    latest = latest_update(code)
    if not latest or latest.relationship_flag is not RelationshipFlag.CHURN_RISK:
        return profile
    import copy
    p = copy.deepcopy(profile)
    for k in (ActionKind.RETENTION, ActionKind.RELATIONSHIP, ActionKind.STRUCTURAL):
        p.kind_weights[k.name] = p.kind_weights.get(k.name, 1.0) * LIVE_CHURN_RETENTION_BOOST
    for k in (ActionKind.UPSELL, ActionKind.WHITESPACE):
        p.kind_weights[k.name] = p.kind_weights.get(k.name, 1.0) * LIVE_CHURN_SELL_DEMOTE
    return p


def current_actions(code: str, n: int = 3) -> List[Candidate]:
    profile = _tilt_for_relationship(code, load_profile(code))
    ranked = rank_candidates(_live_pool(code), profile)
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
        "origin": c.origin,
    }


def customer_summary(code: str) -> dict:
    eng = _engine()
    p = eng["profiles"][code]
    profile = load_profile(code)
    notes = effective_context(code)  # fresh: includes WhatsApp updates saved since start-up
    relationship = notes.relationship if notes else p.relationship
    live = live_hook_set(code)
    latest = latest_update(code)
    muted = mute.active(code, p.order_dates[-1] if p.order_dates else None)
    hooks = list(notes.hooks) if notes else []
    return {
        "code": code,
        "name": p.customer.name,
        "segment": p.segment.value,
        "flag": relationship.value,
        "flag_key": relationship.name,
        "rfm": p.rfm_code,
        "balance": p.customer.balance_owing,
        "kind": CUSTOMER_KIND.get(code, ""),
        "contact": {
            "name": p.contact.name,
            "phone": p.contact.phone,
            "email": p.contact.email,
        },
        "hooks": hooks,
        "hook_items": [{"text": h, "live": h in live} for h in hooks],
        "advice": latest.advice if latest else "",
        "intel_updated": latest.ts if latest else "",
        "intel_count": len(load_updates(code)),
        "next_contact": (notes.next_contact if notes else "") or "",
        "snapshot": (f"{p.frequency} orders · ${p.monetary:,.0f} in 24 months · "
                     + (f"last order {p.recency_days} days ago" if p.recency_days is not None
                        else "no orders on record")),
        "last_order_days": p.recency_days,
        "orders": p.frequency,
        "spend": p.monetary,
        # Spend is invoiced minus credits. Both halves ship so a rep can see
        # WHY the number is lower than the invoices suggest, and so a shop that
        # sends most of it back isn't pitched more stock to sit on.
        "invoiced": p.invoiced,
        "credited": p.credited,
        "return_rate": p.return_rate,
        "heavy_returner": p.heavy_returner,
        "top_groups": [g.name for g in p.bought_groups[:4]],
        "learned": learned_chips(profile),
        # "do not alert again" (utils/mute.py). This page is where a rep turns
        # it back on by hand — a muted account never appears in the queue.
        "muted": muted.note if muted else None,
        "is_muted": muted is not None,
    }


def all_profiles() -> Dict[str, "CustomerProfile"]:
    """code -> CustomerProfile for every active customer (cached engine)."""
    return _engine()["profiles"]


def is_known_customer(code: str) -> bool:
    return code in _engine()["profiles"]


def account_card(code: str) -> dict:
    """Lean list-row view of a customer (the full summary is per-visit)."""
    p = _engine()["profiles"][code]
    notes = effective_context(code)
    relationship = notes.relationship if notes else p.relationship
    return {
        "code": code,
        "name": p.customer.name,
        "segment": p.segment.value,
        "flag": relationship.value,
        "flag_key": relationship.name,
        "balance": p.customer.balance_owing,
        "spend": p.monetary,
        "orders": p.frequency,
        "last_order_days": p.recency_days,
        "return_rate": p.return_rate,
        "heavy_returner": p.heavy_returner,
    }


def customer_list() -> List[dict]:
    """Every active customer, biggest 24-month spend first."""
    return [account_card(code) for code in _engine()["profiles"]]


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

def _note_idea(candidate_id: str, accepted: bool) -> None:
    """A tap on a playbook card is the only thing that changes how far that
    idea travels — every rep's taps, not just this customer's."""
    if IDEA_ID_MARKER in (candidate_id or ""):
        playbook.note_outcome(candidate_id.split(IDEA_ID_MARKER)[-1], accepted)

def submit_feedback(code: str, accepted_ids: List[str], rejections: List[dict],
                    n: int = 3) -> dict:
    """rejections: [{id, reasons:[ReasonName], note}]. Persists, returns the
    refreshed action set."""
    from constants.feedback import RejectionReason  # local import avoids cycle at top
    by_id = {c.id: c for c in _live_pool(code)}
    profile = load_profile(code)

    for acc in accepted_ids or []:
        apply_acceptance(profile, acc)
        _note_idea(acc, accepted=True)

    for rej in rejections or []:
        cand = by_id.get(rej.get("id"))
        if not cand:
            continue
        _note_idea(rej.get("id"), accepted=False)
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


# --- Live intel API helpers -------------------------------------------------

def group_names() -> List[str]:
    return _engine()["groups"]


def intel_payload(code: str) -> dict:
    return {"code": code, "updates": [u.to_dict() for u in load_updates(code)]}
