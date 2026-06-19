"""Render a CustomerProfile (+ its actions) into a one-page Markdown report.

`resolve` is a callable code -> (description, price, stock_label|None) so the
report quotes live product facts rather than duplicating them.
"""
from typing import Callable, Optional, Tuple

from constants.config import ANCHOR_DATE
from constants.recommended_actions import Action, CUSTOMER_KIND
from utils.profile import CustomerProfile

Resolver = Callable[[str], Tuple[str, Optional[float], Optional[str]]]


def _money(v: Optional[float]) -> str:
    return "price n/a" if v is None else f"${v:,.0f}"


def _date(d) -> str:
    return d.strftime("%d %b %Y") if d else "—"


def _monetary_caveat(p: CustomerProfile) -> str:
    hooks = " ".join(p.notes.hooks).lower() if p.notes else ""
    if "returns" in hooks or "consignment" in hooks:
        return " _(gross; returns are not netted in the data — true retained revenue is lower)_"
    return ""


def _pitch_line(pitch, resolve: Resolver) -> str:
    desc, price, stock = resolve(pitch.code)
    stock_txt = f", {stock.lower()}" if stock else ""
    why = f" — {pitch.why}" if pitch.why else ""
    return f"  - **`{pitch.code}`** — {desc} ({_money(price)}{stock_txt}){why}"


def _action_block(idx: int, action: Action, resolve: Resolver) -> str:
    lines = [f"#### {idx}. {action.title}", "", action.detail, ""]
    if action.pitches:
        lines.append("**Specific products:**")
        lines += [_pitch_line(p, resolve) for p in action.pitches]
        lines.append("")
    if action.groups:
        lines.append("**Product group(s):** " + ", ".join(f"`{g}`" for g in action.groups))
        lines.append("")
    if action.incentive:
        lines.append(f"**Proposed incentive (⚠ needs head-office approval):** {action.incentive}")
        lines.append("")
    if action.grounded_in:
        lines.append(f"*Basis:* {action.grounded_in}")
        lines.append("")
    return "\n".join(lines)


def render(profile: CustomerProfile, actions, resolve: Resolver) -> str:
    p = profile
    seg = p.segment.value
    flag = p.relationship.value
    bal = p.customer.balance_owing

    out = []
    out.append(f"# Sales Action Report — {p.customer.name} (`{p.customer.code}`)")
    out.append(
        f"*Snapshot: Unleashed exports as of {ANCHOR_DATE:%d %b %Y}. "
        f"POC — recommended actions are proposals pending head-office approval.*"
    )
    out.append("")

    # --- Segment & RFM ---
    out.append("## Segment & RFM")
    line = f"**Segment: {seg}**  ·  RFM **{p.rfm_code}**  (R{p.r} · F{p.f} · M{p.m})"
    if flag:
        line += f"  \n> ⚠ **Relationship flag:** {flag}"
    out.append(line)
    out.append("")
    out.append("| | Value | Score |")
    out.append("|---|---|---|")
    out.append(f"| **Recency** | {p.recency_days} days since last order ({_date(p.last_order_date)}) | **{p.r}** / 5 |")
    out.append(f"| **Frequency** | {p.frequency} distinct orders in 24 months | **{p.f}** / 5 |")
    out.append(f"| **Monetary** | {_money(p.monetary)} invoiced in 24 months{_monetary_caveat(p)} | **{p.m}** / 5 |")
    out.append("")

    # --- Balance flag ---
    if bal > 0:
        out.append(f"> 💰 **BALANCE OWING: ${bal:,.0f}** — factor into any incentive/credit discussion.")
    else:
        out.append("> ✅ **No balance owing.**")
    out.append("")

    # --- Snapshot + kind ---
    snapshot = (
        f"{p.frequency} orders and {_money(p.monetary)} invoiced over 24 months; "
        f"last ordered {p.recency_days} days ago ({_date(p.last_order_date)}). "
        f"Scores **{seg}** on the numbers — {flag.split('—')[0].strip().lower() if flag else 'no qualitative flag'}."
    )
    out.append(f"**Snapshot.** {snapshot}")
    out.append("")
    out.append(f"**What kind of customer.** {CUSTOMER_KIND.get(p.customer.code, '')}")
    out.append("")

    # --- Meeting-notes context ---
    out.append("## Meeting-notes context")
    if p.notes:
        out.append(p.notes.narrative)
        out.append("")
        if p.notes.hooks:
            out.append("**Key signals:**")
            out += [f"- {h}" for h in p.notes.hooks]
            out.append("")

    # --- Buying behaviour & opportunities ---
    out.append("## What they buy & where the room is")
    if p.bought_groups:
        top = p.bought_groups[:5]
        out.append("**Top product groups bought (24mo spend):** " +
                   "; ".join(f"{g.name} ({_money(g.spend)})" for g in top))
    else:
        out.append("**Top product groups bought:** none on record (no real product lines).")
    out.append("")
    out.append(
        f"**New products since last order:** {p.new_since_count} in pitchable groups — "
        f"{len(p.new_in_bought_in_stock)} in-stock inside groups they already buy "
        f"(+{len(p.new_in_bought_backorder)} backorder)."
    )
    if p.whitespace_groups:
        ws = p.whitespace_groups[:4]
        out.append("")
        out.append("**White-space (never bought, new stock available):** " +
                   "; ".join(f"{g.name} ({g.lines} items, ~{_money(g.spend)})" for g in ws))
    out.append("")

    # --- Actions ---
    out.append("## Recommended actions")
    for idx, action in enumerate(actions, start=1):
        out.append(_action_block(idx, action, resolve))

    # --- Future-tool feedback stub ---
    out.append("## Rep response — _for the next iteration_")
    out.append("*If these actions are rejected, note why so the tool can propose better ones next time.*")
    for idx in range(1, len(actions) + 1):
        out.append(f"- [ ] **Action {idx}** — accepted / rejected · reason: ______________________")
    out.append("")
    out.append("---")
    out.append(
        "*Data: Unleashed Products, View Products, Sales Enquiry & Invoice Enquiry exports "
        f"(as of {ANCHOR_DATE:%d %b %Y}) + meeting notes. Monetary = gross invoiced (returns not netted). "
        "Balance is a manual head-office input (not in Unleashed).*"
    )
    return "\n".join(out)
