"""Step 2 + Step 3 checkpoint: compute RFM and the upsell matches for all five
target customers and print them for review (no report files written yet).

Run:  python3 analyze.py
"""
from constants.config import ANCHOR_DATE
from utils.profile import build_profiles


def money(v: float) -> str:
    return f"${v:,.0f}"


def main() -> None:
    profiles = build_profiles()

    print(f"\nANCHOR (snapshot) DATE: {ANCHOR_DATE:%d %b %Y}\n")
    print("=" * 96)
    print("STEP 2 — RFM SCORECARD")
    print("=" * 96)
    hdr = f"{'Code':8} {'Customer':26} {'Rec(d)':>6} {'R':>1} {'Freq':>4} {'F':>1} {'Monetary':>10} {'M':>1}  {'RFM':>3}  Segment"
    print(hdr)
    print("-" * 96)
    for p in profiles:
        print(f"{p.customer.code:8} {p.customer.name[:26]:26} "
              f"{(p.recency_days if p.recency_days is not None else -1):>6} {p.r:>1} "
              f"{p.frequency:>4} {p.f:>1} {money(p.monetary):>10} {p.m:>1}  "
              f"{p.rfm_code:>3}  {p.segment.value}")
    print()
    for p in profiles:
        flag = p.relationship.value or "—"
        bal = f"  | BALANCE OWING {money(p.customer.balance_owing)}" if p.customer.balance_owing else ""
        print(f"  {p.customer.code}: {flag}{bal}")

    print("\n" + "=" * 96)
    print("STEP 3 — UPSELL ENGINE (product matching)")
    print("=" * 96)
    for p in profiles:
        print(f"\n### {p.customer.code} — {p.customer.name}  [{p.segment.value}]")
        print(f"    last order {p.last_order_date}  | {p.frequency} orders "
              f"({p.product_order_count} with real products) | "
              f"{p.new_since_count} products created since last order")

        print(f"    Top product groups bought (spend):")
        if p.bought_groups:
            for g in p.bought_groups[:6]:
                print(f"        {g.spend:>12,.0f}  {g.lines:>4} ln  {g.name}")
        else:
            print("        (none — no real product lines on record)")

        print(f"    NEW in-stock products INSIDE bought groups: {len(p.new_in_bought_in_stock)} "
              f"(+{len(p.new_in_bought_backorder)} backorder)")
        for i in p.new_in_bought_in_stock[:5]:
            print(f"        {i.code:18} {money(i.sell_price):>8}  [{i.group}]  {i.description[:46]}")

        print(f"    WHITE-SPACE groups (never bought, have NEW in-stock stock): "
              f"{len(p.whitespace_groups)}")
        for g in p.whitespace_groups[:6]:
            print(f"        {g.lines:>3} new in-stock  ~{money(g.spend)} value  {g.name}")

    print("\n(Checkpoint only — no report files written yet.)\n")


if __name__ == "__main__":
    main()
