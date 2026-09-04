"""Assemble a CustomerProfile per target customer: RFM inputs/scores/segment,
the product groups they buy, and the upsell matches (new products in bought
groups, plus 'white space' groups they've never bought that have new stock).

This is the structured object the reports render from — and the natural place
for the future tool to attach rep feedback / preferences.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from constants.columns import (
    CustomerCol,
    InvoiceCol,
    SalesCol,
    SalesStatus,
)
from constants.config import ANCHOR_DATE
from constants.customers import TARGET_BY_CODE, TARGET_CODES, TargetCustomer
from constants.meeting_notes import MeetingContext
from utils.intel import effective_context
from constants.products import EXCLUDED_GROUPS, EXCLUDED_PRODUCT_CODES, canonical_group
from constants.rfm import RelationshipFlag, Segment
from utils.datasource import customer_rows, invoice_rows, sales_rows
from utils.products import (
    CatalogueItem,
    load_catalogue,
    load_product_master,
    new_since,
    rank_items,
)
from utils.parsing import days_between, parse_date, parse_money
from utils.rfm import rfm_segment, score_frequency, score_monetary, score_recency


@dataclass(frozen=True)
class BoughtGroup:
    name: str
    lines: int
    spend: float


@dataclass(frozen=True)
class ContactInfo:
    name: str = ""
    phone: str = ""
    email: str = ""

    def __bool__(self) -> bool:
        return bool(self.name or self.phone or self.email)


@dataclass
class CustomerProfile:
    customer: TargetCustomer
    # RFM inputs
    last_order_date: Optional[date]
    last_invoice_date: Optional[date]
    recency_days: Optional[int]
    frequency: int           # distinct orders (all)
    product_order_count: int  # distinct orders containing a real product line
    monetary: float          # gross invoiced, 24mo
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

    @property
    def rfm_code(self) -> str:
        return f"{self.r}{self.f}{self.m}"

    @property
    def bought_group_names(self) -> set:
        return {g.name for g in self.bought_groups}


def _bucket_sales():
    """One pass over the sales file -> {code: [rows]} for the targets only."""
    buckets: Dict[str, list] = defaultdict(list)
    for row in sales_rows():
        if row.get(SalesCol.STATUS) != SalesStatus.COMPLETED:
            continue  # skips the stray 'Totals' footer too
        code = (row.get(SalesCol.CUSTOMER_CODE) or "").strip()
        if code in TARGET_CODES:
            buckets[code].append(row)
    return buckets


def _bucket_invoices():
    buckets: Dict[str, list] = defaultdict(list)
    for row in invoice_rows():
        code = (row.get(InvoiceCol.CUSTOMER_CODE) or "").strip()
        if code in TARGET_CODES:
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


def _customer_master() -> Dict[str, dict]:
    """Customer-master rows keyed by code (Unleashed sync only; {} on CSV)."""
    return {
        (row.get(CustomerCol.CODE) or "").strip(): row
        for row in customer_rows()
        if (row.get(CustomerCol.CODE) or "").strip() in TARGET_CODES
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
        master_phone = ((master_row.get(CustomerCol.MOBILE) or "").strip()
                        or (master_row.get(CustomerCol.PHONE) or "").strip())
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


def build_profiles() -> List[CustomerProfile]:
    master = load_product_master()
    catalogue = load_catalogue(master)
    sales = _bucket_sales()
    invoices = _bucket_invoices()
    contact_master = _customer_master()

    profiles: List[CustomerProfile] = []
    for code, customer in TARGET_BY_CODE.items():
        s_rows = sales.get(code, [])
        i_rows = invoices.get(code, [])

        # --- Recency / Frequency from orders ---
        order_dates = [d for d in (parse_date(r.get(SalesCol.ORDER_DATE)) for r in s_rows) if d]
        last_order = max(order_dates) if order_dates else None
        recency = days_between(last_order, ANCHOR_DATE)
        distinct_orders = {(r.get(SalesCol.ORDER_NO) or "").strip() for r in s_rows}
        frequency = len(distinct_orders)
        product_orders = _product_order_codes(s_rows)

        # --- Monetary from invoices (gross) ---
        monetary = sum(parse_money(r.get(InvoiceCol.TOTAL)) for r in i_rows)
        inv_dates = [d for d in (parse_date(r.get(InvoiceCol.COMPLETED_DATE)) for r in i_rows) if d]
        last_invoice = max(inv_dates) if inv_dates else None

        # --- Scores / segment ---
        r = score_recency(recency)
        f = score_frequency(frequency)
        m = score_monetary(monetary)
        segment = rfm_segment(r, f)
        notes = effective_context(code)  # meeting notes + live WhatsApp intel
        relationship = notes.relationship if notes else RelationshipFlag.NONE

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
        ))
    # Keep the brief's ordering.
    order = {c: i for i, c in enumerate(TARGET_BY_CODE)}
    profiles.sort(key=lambda p: order[p.customer.code])
    return profiles
