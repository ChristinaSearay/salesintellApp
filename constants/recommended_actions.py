"""Per-customer 'what kind of customer' summary and the 3 recommended actions.

Actions are structured DATA (not prose buried in the renderer): each names real
product codes and/or groups, carries an explicit PROPOSED incentive where one is
suggested (so head office can approve it against margins), and records what fact
it is grounded in. This shape is deliberate — the future interactive tool will
swap/re-rank these and attach rep feedback per action.

Product prices/descriptions are NOT duplicated here; the renderer resolves each
code live against the product master + catalogue so figures stay fact-checkable.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Pitch:
    code: str
    why: str = ""


@dataclass(frozen=True)
class Action:
    title: str
    detail: str
    pitches: tuple = ()      # tuple[Pitch]
    groups: tuple = ()       # exact Product Group names referenced
    incentive: str = ""      # explicit PROPOSED incentive; "" if none
    grounded_in: str = ""    # the data/notes fact this rests on


# One-line "what kind of customer" descriptor (authored from data + notes).
CUSTOMER_KIND = {
    "CMJ223": (
        "High-volume, high-frequency chain & pendant buyer who looks like a top "
        "account on paper — but is actively trying to leave after a quality dispute. "
        "Treat as a retention-critical Champion, not a growth account."
    ),
    "AJW093": (
        "Our highest-spend account by dollars, built on gold chain — but stalled: a "
        "big volume deal collapsed and there's been no selling since, with rep-fit "
        "friction in the mix. A Champion to re-activate, carefully."
    ),
    "MJ001": (
        "A mid-tier account whose business ran on open consignment that has stopped "
        "working (stock goes out, comes back). Loyal but declining; needs a new "
        "commercial structure, not more stock on memo."
    ),
    "TCJ1138": (
        "Effectively an un-won prospect: one small order, a warm meeting and a "
        "requested quotation that never converted. Re-engagement/qualification case, "
        "not a lapsed regular."
    ),
    "S141": (
        "A small, occasional buyer who orders only as needed and isn't yet ours for "
        "their core gold stock. Upside is becoming their preferred 9k/18k gold "
        "supplier and introducing equipment they don't know we carry."
    ),
}


RECOMMENDED_ACTIONS = {
    # ---------------- Class A (Champion, CHURN RISK, owes $2,862) -------------
    "CMJ223": (
        Action(
            title="Close out the 9KC239 quality complaint that triggered the walkout",
            detail=(
                "The defection started with Brad's quality complaint about pendant "
                "9KC239. Lead the next contact by owning it: collect/inspect the faulty "
                "piece, issue a replacement, and review the recent Pendants (No Stones) "
                "batch (a $11k group for them). Pair the goodwill with the outstanding "
                "$2,862 balance so the conversation resets the relationship rather than "
                "chasing money."
            ),
            pitches=(Pitch("9KC239", "the specific item complained about"),),
            groups=("Pendants (No Stones)",),
            incentive=(
                "PROPOSED: free replacement of the faulty 9KC239 unit(s) + a goodwill "
                "credit against the $2,862 balance (e.g. waive a defined portion) — "
                "pending head-office approval."
            ),
            grounded_in="Meeting notes (quality complaint, supply pulled) + $2,862 balance owing.",
        ),
        Action(
            title="Re-open the warm thread — lab grown diamond bracelets for Sam (2IC)",
            detail=(
                "Sam showed unprompted interest in lab grown diamond bracelets and we "
                "already made samples. We now hold matching stock, so the samples "
                "'landing' is a natural, low-pressure reason to re-engage Sam directly "
                "(not Brad). Lab Grown Jewellery is white-space for this account — they "
                "have never bought from it."
            ),
            pitches=(
                Pitch("9KLDBT800W18CM", "lab grown diamond tennis bracelet, in stock"),
                Pitch("9KLDBT55018CM", "yellow-gold lab grown diamond tennis bracelet, in stock"),
            ),
            groups=("Lab Grown Jewellery", "Diamond Bracelets"),
            incentive=(
                "PROPOSED: offer the already-made samples at sample/intro pricing, or a "
                "first small parcel on sale-or-return — pending approval."
            ),
            grounded_in="Meeting notes (Sam's interest, samples made) + live Lab Grown stock.",
        ),
        Action(
            title="Protect the core chain business before they switch suppliers",
            detail=(
                "They are a top chain buyer over 24 months — Cable | Trace | Oval Link "
                "Chains $48.6k, Paperclip Chains $31.6k, Belcher Chains $20.3k. With "
                "churn risk live, don't wait for the next order: propose a standing "
                "replenishment / priority stock hold on these exact lines so a competitor "
                "can't get a foot in on availability."
            ),
            groups=("Cable | Trace | Oval Link Chains", "Paperclip Chains", "Belcher Chains"),
            incentive=(
                "PROPOSED: loyalty/volume rebate on a committed quarterly chain order "
                "(rate TBD) — pending margin approval. No rate is implied here."
            ),
            grounded_in="Their 24-month bought-group spend (Sales Enquiry).",
        ),
    ),
    # ---------------- Atlas (Champion, STALLED) ------------------------------
    "AJW093": (
        Action(
            title="Re-table the gold-chain volume deal — restructured and de-risked",
            detail=(
                "They agreed then walked from a $100k gold-chain deal at $100/g (vs the "
                "$120/g standard), officially citing cash pressure. Their core spend is "
                "Curb Chains $63.7k (119 lines), Figaro Chains $28.2k and Cable | Trace "
                "$19.8k. Re-approach with a smaller staged commitment (e.g. a $25–50k "
                "tranche) at a similar per-gram incentive, removing the all-at-once cash "
                "risk that supposedly killed it."
            ),
            groups=("Curb Chains", "Figaro Chains"),
            incentive=(
                "PROPOSED: re-offer ~$100–105/g (vs $120/g standard) on a staged tranche "
                "basis, anchored to the prior $100/g figure — pending head-office approval."
            ),
            grounded_in="Meeting notes (the $100/g deal) + 24-month bought-group spend.",
        ),
        Action(
            title="Change the face of the relationship before re-selling",
            detail=(
                "Venos has gone cold and reportedly dislikes rep Gabby (he's close with a "
                "competitor of hers); there's been no selling attempt since the deal fell "
                "over. Route the re-approach through a different rep or an owner-level "
                "contact to reset, and attach it to the concrete new-product intro below "
                "so it isn't purely a relationship call."
            ),
            grounded_in="Meeting notes (rep friction, no contact since).",
        ),
        Action(
            title="Open Lab Grown Jewellery as new margin — adjacent to their diamond bracelets",
            detail=(
                "Atlas already sells Diamond Bracelets ($13.2k with us). Lab Grown "
                "Jewellery is white-space for them with ~$23.5k of new in-stock product — "
                "an on-trend, higher-margin extension of a category they already move. "
                "Lead with stocked lab grown diamond bracelets."
            ),
            pitches=(
                Pitch("9KLDBT800W18CM", "lab grown diamond tennis bracelet, in stock"),
                Pitch("9KLDBT55018CM", "lab grown diamond tennis bracelet, in stock"),
            ),
            groups=("Lab Grown Jewellery",),
            incentive="PROPOSED: intro terms on a first lab-grown parcel — pending approval.",
            grounded_in="White-space engine (never bought, new in-stock) + their Diamond Bracelets history.",
        ),
    ),
    # ---------------- My Jewellers (Loyal, DECLINING) ------------------------
    "MJ001": (
        Action(
            title="Replace open consignment with a capped, curated structure for mid-July",
            detail=(
                "The open consignment has failed — last drop ~$30k sent, all but $1k "
                "returned, and the gross invoiced figure ($91.7k) badly overstates what "
                "they actually retained. For the mid-July attempt, propose a small "
                "curated parcel (e.g. ≤$10k) on defined sale-or-return terms: capped "
                "value, fixed 60-day window, deposit and a restock fee on returns — "
                "instead of an open $20–30k hold."
            ),
            incentive=(
                "PROPOSED: structured memo/SOR — deposit % up front + restocking fee on "
                "returned stock (rates TBD) — pending approval. Explicitly replaces the "
                "old open-ended consignment."
            ),
            grounded_in="Meeting notes (consignment history, returns) + returns caveat on Monetary.",
        ),
        Action(
            title="Lead with one precise high-value piece they already sell",
            detail=(
                "They buy Diamond Bangles ($6.9k with us). A new piece is in stock now: a "
                "9k WG diamond oval hinged bangle. Offer this single proven-category item "
                "as a firm sale (not consignment) to restart paid orders with low risk to "
                "both sides."
            ),
            pitches=(Pitch("9KBFOH5W-52X44MM", "new diamond bangle, in stock, in a group they already buy"),),
            groups=("Diamond Bangles",),
            grounded_in="Their Diamond Bangles history + new-in-stock match (upsell engine).",
        ),
        Action(
            title="Diversify them into firm-sale Lab Grown Jewellery (white-space)",
            detail=(
                "Lab Grown Jewellery is white-space with ~$24.4k of new in-stock product. "
                "Pitch a small paid trial selection to pull them out of the consignment "
                "dynamic into firm-sale, higher-margin lines."
            ),
            pitches=(
                Pitch("9KLDBT55018CM", "lab grown diamond tennis bracelet, in stock"),
                Pitch("9KLDR101WSETSIZEM", "lab grown diamond halo ring set, in stock"),
            ),
            groups=("Lab Grown Jewellery",),
            incentive="PROPOSED: trial pricing on a first small firm-sale selection — pending approval.",
            grounded_in="White-space engine.",
        ),
    ),
    # ---------------- The Cut (Hibernating/Lost, DORMANT PROSPECT) -----------
    "TCJ1138": (
        Action(
            title="Re-send the detailed quotation they asked for — refreshed with new arrivals",
            detail=(
                "Talitha asked for a detailed quotation; we chased ~3 times with no "
                "reply, so the original is stale. Send a fresh, curated quotation built "
                "around new in-stock arrivals in high-interest groups — Letter Pendants "
                "(73 new in stock), Lab Grown Jewellery, and their one prior line, Belcher "
                "Chains."
            ),
            pitches=(
                Pitch("9KLDBT55018CM", "lab grown diamond tennis bracelet, in stock"),
                Pitch("9KCH471RU19.5CM", "9k ruby bracelet, in stock"),
                Pitch("9KBELY050H24CM", "9k belcher chain, in stock — their prior category"),
            ),
            groups=("Letter Pendants", "Lab Grown Jewellery", "Belcher Chains"),
            grounded_in="Meeting notes (requested quotation) + white-space/new-stock engine.",
        ),
        Action(
            title="Anchor the reopener on Belcher Chains — the one line they bought",
            detail=(
                "Their single order was Belcher Chains ($1.3k). New Belcher stock is in "
                "now across price points, which is the lowest-friction reason to re-open "
                "the conversation on proven ground."
            ),
            pitches=(
                Pitch("9KHRL10760CM", "premium 9k belcher chain, in stock"),
                Pitch("9KBELY10020CM", "9k belcher bracelet, in stock"),
            ),
            groups=("Belcher Chains",),
            grounded_in="Their only bought group + new-in-stock match.",
        ),
        Action(
            title="Time-box an opening-stock offer tied to the Melbourne launch",
            detail=(
                "Gabby had offered higher pieces for their Melbourne opening weeks, but we "
                "never learned if the store opened. First confirm store status; if it's "
                "live (or imminent), put an opening-order package in front of them with a "
                "deadline so it doesn't drift again."
            ),
            incentive=(
                "PROPOSED: opening-order discount or sale-or-return-lite on opening stock "
                "(terms TBD) — pending approval, and contingent on confirming the store opened."
            ),
            grounded_in="Meeting notes (Melbourne opening, higher pieces offered).",
        ),
    ),
    # ---------------- Noonan's (About to Sleep, OCCASIONAL) ------------------
    "S141": (
        Action(
            title="Make the explicit pitch to become their preferred 9k/18k gold supplier",
            detail=(
                "The stated goal is to win their 9k/18k gold stock. We hold new in-stock "
                "9k gold across lines they already touch — Hoops (they bought $1.1k), "
                "Curb Chains (their $1.7k last order) and gold rings. Lead with a 9k/18k "
                "gold core-range offer rather than one-off items."
            ),
            pitches=(
                Pitch("9KER206Y20", "9k YG hoops, in stock — a group they buy"),
                Pitch("9KDR124SIZEN", "9k YG diamond dress ring, in stock"),
                Pitch("9KBELY050H24CM", "9k YG belcher chain, in stock"),
            ),
            groups=("Hoops (No Stones)", "Curb Chains"),
            incentive=(
                "PROPOSED: preferred-supplier 9k/18k gold pricing — a per-gram rate or "
                "price-match commitment (rate TBD) — pending head-office approval."
            ),
            grounded_in="Meeting notes (become preferred gold supplier) + new 9k gold in-stock.",
        ),
        Action(
            title="Introduce the Yehuda + Napco machines they don't know we distribute",
            detail=(
                "The notes flag likely interest, but they haven't been told we carry these. "
                "For a gold-focused store this is directly useful: Napco gold testers to "
                "verify gold, and Yehuda detectors to screen lab-grown diamonds. Bring "
                "specs and pricing to the next visit."
            ),
            pitches=(
                Pitch("NAP-S1050", "Napco gold tester (balance + printer)"),
                Pitch("NAP-S9500", "Napco gold tester"),
                Pitch("YEH-WATSON", "Yehuda AI lab-grown diamond detector"),
                Pitch("YEH-SHERLOCK", "Yehuda AI lab-grown diamond detector"),
            ),
            incentive="PROPOSED: in-store demo unit or staged payment terms — pending approval.",
            grounded_in="Meeting notes (Yehuda + Napco interest, not yet advised) + master records.",
        ),
        Action(
            title="Add an adjacent religious line — Rosary Chains (white-space)",
            detail=(
                "They buy Religious Pendants, and Rosary Chains is white-space with ~$4.1k "
                "of new in-stock product — a small, natural add-on that fits their mix "
                "without asking them to move far from what they already sell."
            ),
            groups=("Rosary Chains",),
            grounded_in="White-space engine + their Religious Pendants history.",
        ),
    ),
}
