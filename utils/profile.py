"""Assemble a CustomerProfile per target customer: RFM inputs/scores/segment,
the product groups they buy, and the upsell matches (new products in bought
groups, plus 'white space' groups they've never bought that have new stock).

This is the structured object the reports render from — and the natural place
for the future tool to attach rep feedback / preferences.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from constants.columns import (
    CreditCol,
    CreditStatus,
    CustomerCol,
    InvoiceCol,
    SalesCol,
)
from constants.config import anchor_date
from constants.customers import Customer
from constants.meeting_notes import MeetingContext
from utils.intel import effective_context
from constants.products import EXCLUDED_GROUPS, EXCLUDED_PRODUCT_CODES, canonical_group
from constants.returns import (
    HIGH_RETURN_RATE,
    MIN_INVOICED_FOR_RATE,
    MIN_NET_SPEND,
)
from constants.rfm import RelationshipFlag, Segment
from utils.customers import load_customers
from utils.datasource import credit_rows, customer_rows, invoice_rows, sales_rows
from utils.orders import counts_as_order
from utils.products import (
    CatalogueItem,
    load_catalogue,
    load_product_master,
    new_since,
    rank_items,
)
from utils.parsing import days_between, normalise_phone, parse_date, parse_money, parse_number
from utils.relationship import effective_flag
from utils.rfm import rfm_segment, score_frequency, score_monetary, score_recency


@dataclass(frozen=True)
class BoughtGroup:
    name: str
    lines: int
    spend: float


@dataclass(frozen=True)
class Purchase:
    """One real product line on one of their orders (noise already excluded).
    The raw material for the repeat-buying engine (utils/repeat.py)."""
    code: str
    description: str
    group: str
    when: date
    quantity: float
    value: float


@dataclass(frozen=True)
class ContactInfo:
    name: str = ""
    phone: str = ""
    email: str = ""

    def __bool__(self) -> bool:
        return bool(self.name or self.phone or self.email)


@dataclass
class CustomerProfile:
    customer: Customer
    # RFM inputs
    last_order_date: Optional[date]
    last_invoice_date: Optional[date]
    recency_days: Optional[int]
    frequency: int           # distinct orders (all)
    product_order_count: int  # distinct orders containing a real product line
    monetary: float          # NET spend, 24mo: invoiced minus credits, floored at 0
    invoiced: float          # gross invoiced, 24mo (what monetary used to be)
    credited: float          # credit notes, 24mo — what they sent back
    sales_line_count: int
    # RFM outputs
    r: int
    f: int
    m: int
    segment: Segment
    relationship: RelationshipFlag
    notes: MeetingContext
    # Product analysis
    bought_groups: List[BoughtGroup] = field(default_factory=list)
    new_in_bought_in_stock: List[CatalogueItem] = field(default_factory=list)
    new_in_bought_backorder: List[CatalogueItem] = field(default_factory=list)
    whitespace_groups: List[BoughtGroup] = field(default_factory=list)  # group + #new in-stock + value
    new_since_count: int = 0
    contact: ContactInfo = field(default_factory=ContactInfo)
    bought_product_codes: frozenset = frozenset()  # every product code on their orders
    purchases: Tuple[Purchase, ...] = ()           # real product lines, for cadence analysis
    order_dates: Tuple[date, ...] = ()             # distinct order dates, oldest first

    @property
    def rfm_code(self) -> str:
        return f"{self.r}{self.f}{self.m}"

    @property
    def return_rate(self) -> float:
        """Share of invoiced value sent back (0.0-1.0), or 0.0 when there isn't
        enough invoiced to mean anything — one returned parcel against two
        orders is 100% and tells a rep nothing."""
        if self.invoiced < MIN_INVOICED_FOR_RATE:
            return 0.0
        return min(1.0, self.credited / self.invoiced)

    @property
    def heavy_returner(self) -> bool:
        """Sends back enough that pitching more stock to sit on is a mistake."""
        return self.return_rate >= HIGH_RETURN_RATE

    @property
    def bought_group_names(self) -> set:
        return {g.name for g in self.bought_groups}


def _bucket_sales(codes: frozenset):
    """One pass over the sales file -> {code: [rows]} for the wanted customers."""
    buckets: Dict[str, list] = defaultdict(list)
    for row in sales_rows():
        if not counts_as_order(row):
            continue  # skips parked drafts and the stray 'Totals' footer too
        code = (row.get(SalesCol.CUSTOMER_CODE) or "").strip()
        if code in codes:
            buckets[code].append(row)
    return buckets


def _bucket_invoices(codes: frozenset):
    buckets: Dict[str, list] = defaultdict(list)
    for row in invoice_rows():
        code = (row.get(InvoiceCol.CUSTOMER_CODE) or "").strip()
        if code in codes:
            buckets[code].append(row)
    return buckets


def _bucket_credits(codes: frozenset):
    """Completed credit notes per customer. A Parked credit is a draft nobody
    has approved, so it hasn't given the customer their money back yet."""
    buckets: Dict[str, list] = defaultdict(list)
    for row in credit_rows():
        if (row.get(CreditCol.STATUS) or "").strip() not in CreditStatus.COUNTED:
            continue
        code = (row.get(CreditCol.CUSTOMER_CODE) or "").strip()
        if code in codes:
            buckets[code].append(row)
    return buckets


def _bought_groups(sales_rows) -> List[BoughtGroup]:
    """Aggregate real (non-noise) product groups the customer has ordered,
    ranked by spend then line count."""
    agg = defaultdict(lambda: [0, 0.0])  # group -> [lines, spend]
    for row in sales_rows:
        if (row.get(SalesCol.PRODUCT_CODE) or "").strip() in EXCLUDED_PRODUCT_CODES:
            continue
        group = canonical_group(row.get(SalesCol.PRODUCT_GROUP))
        if not group or group in EXCLUDED_GROUPS:
            continue
        agg[group][0] += 1
        agg[group][1] += parse_money(row.get(SalesCol.SUB_TOTAL))
    groups = [BoughtGroup(g, v[0], v[1]) for g, v in agg.items()]
    return sorted(groups, key=lambda g: (-g.spend, -g.lines, g.name))


def _purchases(sales_rows) -> Tuple[Purchase, ...]:
    """Real product lines only — the same noise exclusions as _bought_groups,
    which matters: freight/sundry lines are the most 'repeatedly bought' of all."""
    out = []
    for row in sales_rows:
        code = (row.get(SalesCol.PRODUCT_CODE) or "").strip()
        if not code or code in EXCLUDED_PRODUCT_CODES:
            continue
        group = canonical_group(row.get(SalesCol.PRODUCT_GROUP))
        if not group or group in EXCLUDED_GROUPS:
            continue
        when = parse_date(row.get(SalesCol.ORDER_DATE))
        if not when:
            continue
        out.append(Purchase(
            code=code,
            description=(row.get(SalesCol.PRODUCT) or "").strip(),
            group=group,
            when=when,
            quantity=parse_number(row.get(SalesCol.QUANTITY)),
            value=parse_money(row.get(SalesCol.SUB_TOTAL)),
        ))
    return tuple(out)


def _customer_master(codes: frozenset) -> Dict[str, dict]:
    """Customer-master rows keyed by code (Unleashed sync only; {} on CSV)."""
    return {
        (row.get(CustomerCol.CODE) or "").strip(): row
        for row in customer_rows()
        if (row.get(CustomerCol.CODE) or "").strip() in codes
    }


def _contact(s_rows, master_row: Optional[dict]) -> ContactInfo:
    """The customer's contact card. Baseline: per field, the value on the most
    recent order that filled it in (orders can list several people — e.g.
    Class A alternates Brad / accounts / Sam — so fields are resolved
    independently). The customer master from the Unleashed sync, when present,
    overrides field-by-field, preferring mobile over landline."""
    name = phone = email = ""
    dated = sorted(
        s_rows,
        key=lambda r: parse_date(r.get(SalesCol.ORDER_DATE)) or date.min,
        reverse=True,
    )
    for row in dated:
        name = name or (row.get(SalesCol.CONTACT_NAME) or "").strip()
        phone = phone or (row.get(SalesCol.CONTACT_PHONE) or "").strip()
        email = email or (row.get(SalesCol.CONTACT_EMAIL) or "").strip()
        if name and phone and email:
            break
    if master_row:
        name = (master_row.get(CustomerCol.CONTACT_NAME) or "").strip() or name
        master_phone = (normalise_phone(master_row.get(CustomerCol.MOBILE))
                        or normalise_phone(master_row.get(CustomerCol.PHONE)))
        phone = master_phone or phone
        email = (master_row.get(CustomerCol.EMAIL) or "").strip() or email
    return ContactInfo(name=name, phone=phone, email=email)


def _product_order_codes(sales_rows) -> set:
    """Distinct order numbers that include at least one real product line."""
    orders = set()
    for row in sales_rows:
        if (row.get(SalesCol.PRODUCT_CODE) or "").strip() in EXCLUDED_PRODUCT_CODES:
            continue
        group = canonical_group(row.get(SalesCol.PRODUCT_GROUP))
        if group and group not in EXCLUDED_GROUPS:
            orders.add((row.get(SalesCol.ORDER_NO) or "").strip())
    return orders


def build_profiles(codes: Optional[Iterable[str]] = None) -> List[CustomerProfile]:
    """Profiles for `codes` (in that order), or for every active customer
    (biggest 24-month spend first) when `codes` is None."""
    directory = load_customers()
    wanted = list(directory) if codes is None else [c for c in codes if c in directory]
    wanted_set = frozenset(wanted)
    master = load_product_master()
    catalogue = load_catalogue(master)
    sales = _bucket_sales(wanted_set)
    invoices = _bucket_invoices(wanted_set)
    credits = _bucket_credits(wanted_set)
    contact_master = _customer_master(wanted_set)

    profiles: List[CustomerProfile] = []
    for code in wanted:
        customer = directory[code]
        s_rows = sales.get(code, [])
        i_rows = invoices.get(code, [])
        c_rows = credits.get(code, [])

        # --- Recency / Frequency from orders ---
        # Distinct and sorted up front: s_rows is one row per sales LINE, so the
        # raw dates repeat. Anything reading a rhythm off this needs the gaps
        # between orders, not between line items.
        order_dates = tuple(sorted({
            d for d in (parse_date(r.get(SalesCol.ORDER_DATE)) for r in s_rows) if d
        }))
        last_order = order_dates[-1] if order_dates else None
        recency = days_between(last_order, anchor_date())
        distinct_orders = {(r.get(SalesCol.ORDER_NO) or "").strip() for r in s_rows}
        frequency = len(distinct_orders)
        product_orders = _product_order_codes(s_rows)

        # --- Monetary: invoiced MINUS credits ---
        # Gross invoiced overstates a lot of these accounts — credits run at
        # ~21% of invoiced across the base, and well over half on shops that
        # order broadly and send back what doesn't sell.
        invoiced = sum(parse_money(r.get(InvoiceCol.TOTAL)) for r in i_rows)
        credited = sum(parse_money(r.get(CreditCol.TOTAL)) for r in c_rows)
        monetary = max(MIN_NET_SPEND, invoiced - credited)
        inv_dates = [d for d in (parse_date(r.get(InvoiceCol.COMPLETED_DATE)) for r in i_rows) if d]
        last_invoice = max(inv_dates) if inv_dates else None

        # --- Scores / segment ---
        r = score_recency(recency)
        f = score_frequency(frequency)
        m = score_monetary(monetary)
        # Never ordered and never invoiced: they aren't lapsed, we just haven't
        # sold to them yet (a shop a rep visited and created, typically).
        segment = (Segment.NEW_PROSPECT if not order_dates and not i_rows
                   else rfm_segment(r, f))
        notes = effective_context(code)  # meeting notes + live WhatsApp intel
        # A note can claim they went quiet; the orders decide whether that is
        # still true (utils/relationship.py).
        relationship = effective_flag(
            notes.relationship if notes else RelationshipFlag.NONE,
            order_dates, recency,
        )

        # --- Product analysis ---
        bought = _bought_groups(s_rows)
        bought_names = {g.name for g in bought}
        fresh = new_since(catalogue, last_order)
        in_bought = [i for i in fresh if i.group in bought_names]
        in_bought_ranked = rank_items(in_bought)
        new_in_stock = [i for i in in_bought_ranked if i.in_stock]
        new_backorder = [i for i in in_bought_ranked if not i.in_stock]

        # White-space: groups they've NEVER bought that have new in-stock items.
        ws = defaultdict(lambda: [0, 0.0])  # group -> [#new in-stock, value of those]
        for i in fresh:
            if i.group not in bought_names and i.in_stock:
                ws[i.group][0] += 1
                ws[i.group][1] += i.sell_price
        whitespace = sorted(
            (BoughtGroup(g, v[0], v[1]) for g, v in ws.items()),
            key=lambda g: (-g.lines, -g.spend, g.name),
        )

        profiles.append(CustomerProfile(
            customer=customer,
            last_order_date=last_order,
            last_invoice_date=last_invoice,
            recency_days=recency,
            frequency=frequency,
            product_order_count=len(product_orders),
            monetary=monetary,
            invoiced=invoiced,
            credited=credited,
            sales_line_count=len(s_rows),
            r=r, f=f, m=m,
            segment=segment,
            relationship=relationship,
            notes=notes,
            bought_groups=bought,
            new_in_bought_in_stock=new_in_stock,
            new_in_bought_backorder=new_backorder,
            whitespace_groups=whitespace,
            new_since_count=len(fresh),
            contact=_contact(s_rows, contact_master.get(code)),
            bought_product_codes=frozenset(
                c for c in ((r.get(SalesCol.PRODUCT_CODE) or "").strip() for r in s_rows) if c),
            purchases=_purchases(s_rows),
            order_dates=order_dates,
        ))
    if codes is None:
        profiles.sort(key=lambda p: (-p.monetary, p.customer.name))
    return profiles
