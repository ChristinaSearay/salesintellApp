"""Structured meeting-notes context, keyed by customer code.

`narrative` is reproduced faithfully from Meeting Notes.docx for the report's
context section. The structured fields (relationship flag, product/group hooks,
incentives already floated, next-contact timing) are the analyst's read of that
text and drive the recommended actions. Keeping them as data makes the future
"learning" tool straightforward: rejections/preferences can attach here.
"""
from dataclasses import dataclass, field

from constants.rfm import RelationshipFlag


@dataclass(frozen=True)
class MeetingContext:
    narrative: str
    relationship: RelationshipFlag
    # Product groups worth pitching given the conversation (exact File 1 names).
    opportunity_groups: tuple = ()
    # Specific product codes referenced in the notes (e.g. a quality complaint).
    referenced_products: tuple = ()
    # An incentive already discussed with the customer (verbatim), if any.
    prior_incentive: str = ""
    # Free-form hooks the report should surface.
    hooks: tuple = ()
    next_contact: str = ""


MEETING_NOTES = {
    "CMJ223": MeetingContext(
        narrative=(
            "Last meeting went badly. Brad (owner) called Christina to complain about "
            "the quality of one of our pendants, 9KC239, and decided to pull supply from "
            "Searay. Although he said he would pull supply, his team has since made "
            "enquiries and placed one small order — but we feel fairly certain he is "
            "trying to move to a different supplier. In the meeting prior, Christina/Gabby "
            "met Brad's second-in-charge, Sam, who was interested in various lab grown "
            "diamond bracelets that we made samples for (even though they didn't ask). We "
            "plan to let them know when they land, and need a careful strategy because the "
            "relationship is sensitive (and possibly over)."
        ),
        relationship=RelationshipFlag.CHURN_RISK,
        opportunity_groups=("Lab Grown Jewellery", "Diamond Bracelets"),
        referenced_products=("9KC239",),
        hooks=(
            "Quality complaint on pendant 9KC239 was the trigger for pulling supply.",
            "Sam (2IC) unprompted interest in lab grown diamond bracelets; samples made.",
            "Carries an outstanding balance — relationship is sensitive.",
        ),
    ),
    "AJW093": MeetingContext(
        narrative=(
            "Last contact was a phone call with Ron/Venos. The relationship/business had "
            "started to slow and we weren't sure why, so we offered a volume incentive: "
            "$100k of gold chain at a discounted $100/g (vs the standard $120/g). Venos "
            "agreed, then pulled out the day before shipment, citing financial pressure — "
            "we suspect this isn't the real reason and she either found a better deal or "
            "didn't want to deal with us. Our rep Gabby has also noted Venos doesn't like "
            "him, as he is close friends with a business she competes with. There have "
            "been no real sales offers or selling attempts since she pulled out."
        ),
        relationship=RelationshipFlag.STALLED,
        opportunity_groups=("Curb Chains", "Cable | Trace | Oval Link Chains"),
        prior_incentive="$100k gold chain volume deal at $100/g vs standard $120/g",
        hooks=(
            "Agreed then walked away from the $100/g volume gold-chain deal.",
            "Rep friction: Venos dislikes Gabby (close to a competitor) — consider rep/owner contact.",
            "No selling attempt since the deal collapsed.",
        ),
    ),
    "MJ001": MeetingContext(
        narrative=(
            "Orders have dropped off after a consignment deal that originally worked great "
            "but no longer does. At first we sent $20–30k of stock they would hold for a "
            "few months and then pay for (in full or split over months). Over time the "
            "terms stretched, and in the last encounter we sent approx. $30k of stock and "
            "the customer returned all but $1k. We need a new strategy next time we try to "
            "sell — around mid July — that works for both sides."
        ),
        relationship=RelationshipFlag.DECLINING,
        opportunity_groups=("Religious Pendants", "Diamond Pendants"),
        prior_incentive="Open-ended consignment ($20–30k of stock held, pay later) — now unviable",
        hooks=(
            "Consignment terms stretched; last drop ~$30k sent, all but $1k returned.",
            "Gross invoiced figure overstates retained revenue (returns not in the data).",
            "Next selling attempt planned ~mid July 2026 — needs a both-sides strategy.",
        ),
        next_contact="Mid July 2026",
    ),
    "TCJ1138": MeetingContext(
        narrative=(
            "A very beneficial meeting with Talitha/Gabby. Talitha was impressed by the "
            "range and asked for a detailed quotation. Gabby offered some higher pieces "
            "for their opening weeks in Melbourne, however she never followed us up and we "
            "are unsure if the opening went ahead. We followed up on the quotation about "
            "three times but she was either too busy to look or, in the end, did not reply."
        ),
        relationship=RelationshipFlag.DORMANT_PROSPECT,
        opportunity_groups=("Belcher Chains",),
        hooks=(
            "Warm meeting; asked for a detailed quotation but never converted.",
            "Context was a Melbourne store opening — timing/relevance may have lapsed.",
            "Only one small order on record (Sept 2024); essentially an un-won prospect.",
        ),
    ),
    "S141": MeetingContext(
        narrative=(
            "In Oct 2024, Andrew (part-owner) was very down and advised business was not "
            "doing well. They order only as they need; the last order, in Nov 2025, was a "
            "custom order. We believe we are not their preferred gold supplier and want to "
            "become it if they are still selling 9k and 18k gold stock. We also think they "
            "might be interested in the Yehuda + Napco machines — they haven't been "
            "personally advised that we distribute these yet."
        ),
        relationship=RelationshipFlag.OCCASIONAL,
        opportunity_groups=("Hoops (No Stones)", "Curb Chains", "Belcher Chains"),
        hooks=(
            "Goal: become their preferred 9k/18k gold supplier.",
            "Potential interest in Yehuda + Napco machines — not yet told we distribute them.",
            "Orders only as needed; last was a custom order Nov 2025.",
        ),
    ),
}
