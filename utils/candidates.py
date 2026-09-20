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
from constants.config import anchor_date
from constants.recommended_actions import RECOMMENDED_ACTIONS, Pitch
from constants.repeat import (
    GROUP_DUE_RATIO,
    GROUP_RESTOCK_PENALTY,
    ITEM_DUE_RATIO,
    MAX_DUE_DAYS,
    MAX_GROUP_RESTOCK,
    MAX_LAPSED_CARDS,
    MAX_RANGE_EXTENSION,
    MAX_REORDER,
    MIN_RESTOCK_OVERDUE_DAYS,
    MIN_ITEM_PURCHASE_DATES,
    MIN_LAPSED_PURCHASE_DATES,
    RANGE_ANCHOR_ITEMS,
    RANGE_PRICE_TOLERANCE,
)
from utils.products import (
    CatalogueItem,
    is_pitchable,
    new_since,
    newest_in_groups,
    rank_items,
)
from utils.repeat import Cadence, due, group_cadences, item_cadences

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


# --- Repeat-buying candidates (their own rhythm) ---------------------------

def _reorder_candidate(code: str, cad: Cadence, item: CatalogueItem, lapsed: bool) -> Candidate:
    """A specific line of theirs that is due (or overdue) to come round again."""
    days = cad.days_since(anchor_date())
    last = f"{cad.last_bought:%d %b %Y}"
    if lapsed:
        title = f"They've stopped reordering: {cad.group}"
        detail = (f"{cad.description} was a standing line — {cad.times_bought} orders, "
                  f"{cad.interval_phrase}. Nothing since {last} ({days} days). Ask what "
                  f"changed before pitching anything new; it's in stock if they want it back.")
    elif cad.times_bought == MIN_ITEM_PURCHASE_DATES:
        # Two orders is one gap, not a rhythm — say so rather than inventing one.
        title = f"Due to reorder: {cad.group}"
        detail = (f"They've ordered {cad.description} twice ({cad.gap_phrase}), last "
                  f"{cad.last_quantity:,.0f} on {last} — {days} days ago, so another run "
                  f"is about due. It's in stock now.")
    else:
        title = f"Due to reorder: {cad.group}"
        detail = (f"They buy {cad.description} {cad.interval_phrase} — {cad.times_bought} orders, "
                  f"last {cad.last_quantity:,.0f} on {last} ({days} days ago). They're due, "
                  f"and it's in stock now.")
    return Candidate(
        id=f"{code}-reorder-{cad.key}",
        title=title,
        detail=detail,
        kind=ActionKind.REORDER,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.REORDER],
        pitches=(Pitch(cad.key, f"their own line — last bought {cad.last_bought:%b %Y}"),),
        groups=(cad.group,),
        grounded_in=(f"Repeat-buying engine: bought on {cad.times_bought} separate dates, "
                     f"{cad.interval_phrase}."),
        price_point=item.sell_price,
    )


def _restock_candidate(code: str, cad: Cadence, item: CatalogueItem) -> Candidate:
    """A whole range they buy on a rhythm that has gone quiet."""
    days = cad.days_since(anchor_date())
    return Candidate(
        id=f"{code}-restock-{_slug(cad.group)}",
        title=f"Time to restock {cad.group}",
        detail=(f"They order {cad.group} {cad.interval_phrase}, but the last one was "
                f"{days} days ago ({cad.last_bought:%d %b %Y}) — that range is running "
                f"behind. This piece is in stock now."),
        kind=ActionKind.REORDER,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.REORDER] - GROUP_RESTOCK_PENALTY,
        pitches=(Pitch(item.code, "in stock, in the range they're due to restock"),),
        groups=(cad.group,),
        grounded_in=(f"Repeat-buying engine: {cad.times_bought} orders in this group, "
                     f"{cad.interval_phrase}."),
        price_point=item.sell_price,
    )


def _range_extension_candidate(code: str, anchor: Cadence, item: CatalogueItem) -> Candidate:
    """A never-ordered piece sitting beside one of their best sellers."""
    return Candidate(
        id=f"{code}-range-{item.code}",
        title=f"Extend their range: more {item.group}",
        detail=(f"{anchor.description} is one of their best sellers (${anchor.value:,.0f} "
                f"over {anchor.times_bought} orders). This is the same range at a similar "
                f"price, in stock, and they have never ordered it."),
        kind=ActionKind.UPSELL,
        incentive_type=IncentiveType.NONE,
        base_score=KIND_BASE_SCORE[ActionKind.UPSELL],
        pitches=(Pitch(item.code, f"same range and price as their {anchor.description[:40]}"),),
        groups=(item.group,),
        grounded_in="Range engine: same group and price band as one of their best sellers, never ordered.",
        price_point=item.sell_price,
    )


def _restock_pick(cad: Cadence, items: List[Cadence], cat_by_code: dict,
                  catalogue: List[CatalogueItem], used: set) -> Optional[CatalogueItem]:
    """What to put in front of them for an overdue range: their own best line in
    it if we can ship it, else the newest in-stock piece in that range."""
    for c in items:  # already sorted by spend
        if c.group != cad.group or c.key in used:
            continue
        item = cat_by_code.get(c.key)
        if item and item.in_stock:
            return item
    picks = _dedup_by_code(newest_in_groups(catalogue, [cad.group], limit=6, in_stock_only=True), used)
    return picks[0] if picks else None


def _sibling(catalogue: List[CatalogueItem], group: str, price: Optional[float],
             skip: set) -> Optional[CatalogueItem]:
    """The best in-stock piece in `group`, near `price`, that they've never had."""
    lo, hi = ((price * (1 - RANGE_PRICE_TOLERANCE), price * (1 + RANGE_PRICE_TOLERANCE))
              if price else (0.0, float("inf")))
    items = [i for i in catalogue
             if i.group == group and i.in_stock and is_pitchable(i)
             and i.code not in skip and lo <= i.sell_price <= hi]
    return rank_items(items)[0] if items else None


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

    cat_by_code = {i.code: i for i in catalogue}
    fresh_instock = [i for i in new_since(catalogue, profile.last_order_date) if i.in_stock]

    # Cap how many auto candidates we draw from any single group, for variety.
    group_counts: dict = {}

    def can_add(group: str) -> bool:
        return group_counts.get(group, 0) < CAP_PER_GROUP

    def note_group(group: str) -> None:
        group_counts[group] = group_counts.get(group, 0) + 1

    # Their own rhythm first: specific lines that are due to come round again.
    items_cad = item_cadences(profile.purchases)
    reorder_groups = set()
    added = lapsed_added = 0
    for cad in due(items_cad, anchor_date(), ITEM_DUE_RATIO):
        if added >= MAX_REORDER:
            break
        item = cat_by_code.get(cad.key)
        if not item or not item.in_stock or cad.key in used_products or not can_add(cad.group):
            continue
        # Only a line with a real history can have "stopped"; a thin one that
        # quiet is simply stale, and pitching it as a reorder would be a guess.
        lapsed = cad.is_lapsed(anchor_date()) and cad.times_bought >= MIN_LAPSED_PURCHASE_DATES
        if not lapsed and cad.days_since(anchor_date()) > MAX_DUE_DAYS:
            continue
        if lapsed and lapsed_added >= MAX_LAPSED_CARDS:
            continue
        pool.append(_reorder_candidate(code, cad, item, lapsed))
        lapsed_added += lapsed
        used_products.add(cad.key)
        note_group(cad.group)
        reorder_groups.add(cad.group)
        added += 1

    # Then whole ranges that have gone quiet (skipping groups covered above).
    added = 0
    for cad in due(group_cadences(profile.purchases), anchor_date(), GROUP_DUE_RATIO):
        if added >= MAX_GROUP_RESTOCK:
            break
        if cad.group in reorder_groups or not can_add(cad.group):
            continue
        if cad.days_since(anchor_date()) - (cad.interval_days or 0) < MIN_RESTOCK_OVERDUE_DAYS:
            continue
        item = _restock_pick(cad, items_cad, cat_by_code, catalogue, used_products)
        if not item:
            continue
        pool.append(_restock_candidate(code, cad, item))
        used_products.add(item.code)
        note_group(cad.group)
        added += 1

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

    # Extend the range: siblings of their best sellers they've never ordered.
    added = 0
    for anchor in item_cadences(profile.purchases, min_dates=1)[:RANGE_ANCHOR_ITEMS]:
        if added >= MAX_RANGE_EXTENSION:
            break
        if not can_add(anchor.group):
            continue
        sibling = _sibling(catalogue, anchor.group, resolve(anchor.key)[1],
                           used_products | profile.bought_product_codes)
        if not sibling:
            continue
        pool.append(_range_extension_candidate(code, anchor, sibling))
        used_products.add(sibling.code)
        note_group(anchor.group)
        added += 1

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
