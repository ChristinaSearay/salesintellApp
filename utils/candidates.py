"""Build a tagged, rankable pool of candidate actions per customer.

Pool = the 3 hand-authored 'seed' actions (kept on top by default) + auto-
generated actions from the upsell engine (new in-stock items in bought groups,
white-space groups) + meeting-notes opportunity hooks. Each candidate carries
metadata (kind, incentive type, price point) so the preference engine can
re-rank it. A Candidate is shape-compatible with the report renderer.
"""
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from constants.feedback import (
    KIND_BASE_SCORE,
    SEED_BASE_SCORE,
    ActionKind,
    IncentiveType,
    PriceBand,
    price_band,
)
from constants.recommended_actions import RECOMMENDED_ACTIONS, Pitch
from utils.products import (
    CatalogueItem,
    new_since,
    newest_in_groups,
    rank_items,
)

Resolver = Callable[[str], Tuple[str, Optional[float], Optional[str]]]

MAX_UPSELL = 6
MAX_WHITESPACE = 6
MAX_OPPORTUNITY = 4
OPPORTUNITY_PER_GROUP = 2
CAP_PER_GROUP = 2  # at most this many auto candidates from any one group (variety)
# Frequent buyers have (almost) nothing "new since last order", so when the pool
# is thin, top it up with the newest in-stock items in their bought groups.
MIN_AUTO_POOL = 9           # enough for the first set + two "fresh pitches" rounds
MAX_LATEST_IN_RANGE = 6
LATEST_IN_RANGE_PENALTY = 4.0  # ranks just below a genuine new-since-last-order upsell


@dataclass
class Candidate:
    id: str
    title: str
    detail: str
    kind: ActionKind
    incentive_type: IncentiveType
    base_score: float
    pitches: Tuple[Pitch, ...] = ()
    groups: Tuple[str, ...] = ()
    incentive: str = ""
    grounded_in: str = ""
    price_point: Optional[float] = None  # max product price; None = not price-filterable
    is_seed: bool = False

    @property
    def price_band(self) -> Optional[PriceBand]:
        return None if self.price_point is None else price_band(self.price_point)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# --- Seed (curated) metadata inference -------------------------------------

def _infer_kind(title: str) -> ActionKind:
    t = title.lower()
    if any(k in t for k in ("complaint", "protect", "switch", "close out", "retention")):
        return ActionKind.RETENTION
    if any(k in t for k in ("relationship", "face of", " rep")):
        return ActionKind.RELATIONSHIP
    if any(k in t for k in ("machine", "yehuda", "napco", "equipment")):
        return ActionKind.EQUIPMENT
    if any(k in t for k in ("consignment", "structure", "terms", "opening-stock")):
        return ActionKind.STRUCTURAL
    if any(k in t for k in ("white-space", "new margin", "new category", "introduce", "lab grown")):
        return ActionKind.WHITESPACE
    return ActionKind.UPSELL


def _infer_incentive_type(text: str) -> IncentiveType:
    t = (text or "").lower()
    if not t.strip():
        return IncentiveType.NONE
    if "consignment" in t:
        return IncentiveType.CONSIGNMENT
    if "sale-or-return" in t or "sale or return" in t or "memo" in t or "sor" in t:
        return IncentiveType.SALE_OR_RETURN
    if "rebate" in t:
        return IncentiveType.REBATE
    if "price-match" in t or "price match" in t:
        return IncentiveType.PRICE_MATCH
    if "demo" in t or "trial" in t:
        return IncentiveType.DEMO
    if "/g" in t or "discount" in t or "intro pric" in t or "pricing" in t:
        return IncentiveType.DISCOUNT
    if any(k in t for k in ("credit", "goodwill", "free ", "replacement", "waive")):
        return IncentiveType.GOODWILL
    return IncentiveType.NONE


def _seed_price_point(pitches, resolve: Resolver) -> Optional[float]:
    prices = [resolve(p.code)[1] for p in pitches]
    prices = [pr for pr in prices if pr is not None]
    return max(prices) if prices else None


def _seed_candidates(code: str, resolve: Resolver) -> List[Candidate]:
    out = []
    for i, a in enumerate(RECOMMENDED_ACTIONS.get(code, ())):
        out.append(Candidate(
            id=f"{code}-seed-{i}",
            title=a.title,
            detail=a.detail,
            kind=_infer_kind(a.title),
            incentive_type=_infer_incentive_type(a.incentive),
            base_score=SEED_BASE_SCORE - i,  # preserve authored order
            pitches=tuple(a.pitches),
            groups=tuple(a.groups),
            incentive=a.incentive,
            grounded_in=a.grounded_in,
            price_point=_seed_price_point(a.pitches, resolve),
            is_seed=True,
        ))
    return out


# --- Auto-generated candidates ---------------------------------------------

def _upsell_candidate(code: str, item: CatalogueItem) -> Candidate:
    return Candidate(
        id=f"{code}-up-{item.code}",
        title=f"Add new stock they already sell: {item.group}",
        detail=(f"They already buy {item.group}. This piece just arrived in stock — "
                f"an easy add-on to their next order, no new category to sell."),
        kind=ActionKind.UPSELL,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.UPSELL],
        pitches=(Pitch(item.code, "new in stock, in a group they already buy"),),
        groups=(item.group,),
        grounded_in="Upsell engine: new in-stock item inside a bought group.",
        price_point=item.sell_price,
    )


def _whitespace_candidate(code: str, group: str, rep: CatalogueItem, count: int) -> Candidate:
    return Candidate(
        id=f"{code}-ws-{_slug(group)}",
        title=f"Open a new category: {group}",
        detail=(f"They have never bought {group}, and we have {count} new in-stock "
                f"piece(s) ready now — a low-commitment way to widen what they range."),
        kind=ActionKind.WHITESPACE,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.WHITESPACE],
        pitches=(Pitch(rep.code, "new in stock — a sample of this category"),),
        groups=(group,),
        grounded_in="White-space engine: never-bought group with new in-stock stock.",
        price_point=rep.sell_price,
    )


def _latest_in_range_candidate(code: str, item: CatalogueItem) -> Candidate:
    added = f" (added {item.created_on:%d %b %Y})" if item.created_on else ""
    return Candidate(
        id=f"{code}-latest-{item.code}",
        title=f"Newest in a range they buy: {item.group}",
        detail=(f"They buy {item.group} regularly. This is our newest in-stock piece in "
                f"that range{added} and it isn't on any of their orders yet."),
        kind=ActionKind.UPSELL,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.UPSELL] - LATEST_IN_RANGE_PENALTY,
        pitches=(Pitch(item.code, "newest in stock in a group they already buy"),),
        groups=(item.group,),
        grounded_in="Range engine: newest in-stock item in a bought group, never ordered by them.",
        price_point=item.sell_price,
    )


def _opportunity_candidate(code: str, item: CatalogueItem, in_bought: bool) -> Candidate:
    kind = ActionKind.UPSELL if in_bought else ActionKind.WHITESPACE
    return Candidate(
        id=f"{code}-opp-{item.code}",
        title=f"From the last meeting: {item.group}",
        detail=(f"This ties to what was raised in the meeting notes. {item.group} stock "
                f"is in now and worth putting in front of them."),
        kind=kind,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[kind] + 6.0,  # meeting relevance bump
        pitches=(Pitch(item.code, "in stock — relevant to the meeting notes"),),
        groups=(item.group,),
        grounded_in="Meeting-notes opportunity group + live stock.",
        price_point=item.sell_price,
    )


def build_candidate_pool(profile, catalogue: List[CatalogueItem], resolve: Resolver) -> List[Candidate]:
    code = profile.customer.code
    bought = profile.bought_group_names
    pool: List[Candidate] = _seed_candidates(code, resolve)
    used_products = {p.code for c in pool for p in c.pitches}

    fresh_instock = [i for i in new_since(catalogue, profile.last_order_date) if i.in_stock]

    # Cap how many auto candidates we draw from any single group, for variety.
    group_counts: dict = {}

    def can_add(group: str) -> bool:
        return group_counts.get(group, 0) < CAP_PER_GROUP

    def note_group(group: str) -> None:
        group_counts[group] = group_counts.get(group, 0) + 1

    # Upsell: new in-stock items inside bought groups, by value.
    upsell_items = rank_items([i for i in fresh_instock if i.group in bought])
    added = 0
    for item in _dedup_by_code(upsell_items, used_products):
        if added >= MAX_UPSELL:
            break
        if not can_add(item.group):
            continue
        pool.append(_upsell_candidate(code, item))
        used_products.add(item.code)
        note_group(item.group)
        added += 1

    # White-space: never-bought groups with new in-stock stock (one per group).
    ws_groups = {}
    for i in fresh_instock:
        if i.group not in bought:
            ws_groups.setdefault(i.group, []).append(i)
    ranked_ws = sorted(ws_groups.items(), key=lambda kv: (-len(kv[1]), -max(x.sell_price for x in kv[1])))
    for group, items in ranked_ws[:MAX_WHITESPACE]:
        if not can_add(group):
            continue
        rep = rank_items(items)[0]
        pool.append(_whitespace_candidate(code, group, rep, len(items)))
        note_group(group)

    # Meeting-notes opportunities (gives recently-ordered customers depth too).
    # Draw PER opportunity group so one busy group can't starve the others.
    notes = profile.notes
    if notes and notes.opportunity_groups:
        for group in notes.opportunity_groups:
            if not can_add(group):
                continue
            taken = opportunity_candidates(code, catalogue, [group], used_products, bought)
            for c in taken:
                pool.append(c)
                note_group(c.groups[0])

    # Latest-in-range top-up for thin pools (one per bought group, by spend).
    if len(pool) < MIN_AUTO_POOL:
        skip = used_products | profile.bought_product_codes
        added = 0
        for g in profile.bought_groups:
            if added >= MAX_LATEST_IN_RANGE or len(pool) >= MIN_AUTO_POOL:
                break
            if not can_add(g.name):
                continue
            items = _dedup_by_code(newest_in_groups(catalogue, [g.name], limit=10, in_stock_only=True), skip)
            if not items:
                continue
            pool.append(_latest_in_range_candidate(code, items[0]))
            used_products.add(items[0].code)
            note_group(g.name)
            added += 1

    return pool


def opportunity_candidates(code: str, catalogue: List[CatalogueItem], groups, used_products: set,
                           bought, bonus: float = 0.0, why: str = "") -> List[Candidate]:
    """Up to OPPORTUNITY_PER_GROUP newest in-stock items per group, as
    opportunity candidates. Mutates `used_products`. Used for meeting-notes
    groups at pool-build time and for live WhatsApp groups per request."""
    out: List[Candidate] = []
    for group in groups:
        opp = newest_in_groups(catalogue, [group], limit=4, in_stock_only=True)
        taken = 0
        for item in _dedup_by_code(opp, used_products):
            if taken >= OPPORTUNITY_PER_GROUP:
                break
            c = _opportunity_candidate(code, item, item.group in bought)
            if bonus or why:
                c = Candidate(**{**c.__dict__, "base_score": c.base_score + bonus,
                                 "title": f"From the latest WhatsApp update: {item.group}",
                                 "detail": (why or c.detail),
                                 "grounded_in": "Live WhatsApp intel opportunity group + live stock."})
            out.append(c)
            used_products.add(item.code)
            taken += 1
    return out


def _dedup_by_code(items: List[CatalogueItem], used: set) -> List[CatalogueItem]:
    out, seen = [], set()
    for i in items:
        if i.code in used or i.code in seen:
            continue
        seen.add(i.code)
        out.append(i)
    return out
