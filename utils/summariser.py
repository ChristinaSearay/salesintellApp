"""Turn a raw WhatsApp dump into structured per-customer IntelUpdates.

One Claude call with a JSON-schema constrained output; the model matches each
message block to a POC customer (or null when it's about someone else), and
emits hooks / opportunity groups / incentives in the vocabulary the engine
already uses. Nothing is persisted here — the caller shows the proposals to
the rep for confirmation, then saves via utils.intel.add_update().
"""
import os
from typing import Iterable, List

from constants.intel import DEFAULT_INTEL_MODEL, INTEL_MAX_TOKENS, IntelSource, extraction_schema
from utils.customers import load_customers
from utils.intel import IntelUpdate

# Extra ways the team refers to each customer in chat (name fragments, staff).
CUSTOMER_ALIASES = {
    "CMJ223": ("Class A", "Class A Jewellers", "Brad", "Sam"),
    "AJW093": ("Atlas", "Atlas Wetherill Park", "Venos"),
    "MJ001": ("My Jewellers",),
    "TCJ1138": ("The Cut",),
    "S141": ("Noonan's", "Noonans", "Showcase"),
}

SYSTEM_PROMPT = """You read internal WhatsApp messages posted by a jewellery wholesaler's sales team
(Searay) about their retail customers, and turn them into structured account intel for a
sales-prep app.

Rules:
- Split the dump into one update per customer discussed. A message that names no customer
  continues the customer discussed in the message immediately before it.
- Match the customer to the list provided. Match on trading name, nickname, or staff names
  listed as aliases. If a customer is not in the list, set customer_code to null and copy the
  name as written — do NOT force a match (e.g. "Atlas Casula" is NOT "Atlas Wetherill Park").
- hooks: 1–3 short, factual bullets a rep should know before walking in (what happened, what
  they asked for, what they're unhappy about). Plain language, no fluff, past tense.
- opportunity_groups: only product groups from the provided list that the conversation gives
  a reason to pitch. Empty if none.
- referenced_products: product codes mentioned verbatim (e.g. 9KC239). Empty if none.
- prior_incentive: any deal/terms the customer asked for or was offered, verbatim-ish
  (e.g. "gold swap + max $20/g labour"). Empty string if none.
- relationship: CHURN_RISK if they are threatening to leave / say we're too expensive /
  pulled supply; STALLED, DECLINING, DORMANT_PROSPECT, OCCASIONAL per their definitions;
  UNCHANGED if the message gives no signal.
- next_contact: a timing cue if one is stated ("when the new samples land"). Else empty.
- advice: one sentence on what the rep should do next with this customer, given the message."""


def _customer_block(customers) -> str:
    lines = []
    for c in sorted(customers, key=lambda c: c.name.lower()):
        aliases = ", ".join(CUSTOMER_ALIASES.get(c.code, ()))
        lines.append(f"- {c.code}: {c.name}" + (f" (aliases: {aliases})" if aliases else ""))
    return "\n".join(lines)


def summarise(text: str, group_names: Iterable[str],
              source: IntelSource = IntelSource.WHATSAPP) -> List[IntelUpdate]:
    """Raises RuntimeError with a rep-readable message when the API is not
    configured or the call fails."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("The 'anthropic' package is not installed (uv sync).") from exc

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError("Summariser is not configured: set ANTHROPIC_API_KEY in .env.")

    groups = sorted({g for g in group_names if g})
    directory = load_customers()
    client = anthropic.Anthropic()
    user = (f"Customers we track:\n{_customer_block(directory.values())}\n\n"
            f"Product groups we sell:\n" + "\n".join(f"- {g}" for g in groups) +
            f"\n\nWhatsApp dump:\n\"\"\"\n{text.strip()}\n\"\"\"")
    try:
        response = client.messages.create(
            model=os.environ.get("SEARAY_INTEL_MODEL", DEFAULT_INTEL_MODEL),
            max_tokens=INTEL_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema",
                                      "schema": extraction_schema(groups)}},
        )
    except anthropic.AuthenticationError as exc:
        raise RuntimeError("Summariser rejected the API key (ANTHROPIC_API_KEY).") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError("Summariser could not reach the Claude API (network).") from exc
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"Summariser API error {exc.status_code}: {exc.message}") from exc

    if response.stop_reason == "refusal":
        raise RuntimeError("Summariser declined to process this text.")
    import json
    payload = json.loads(next(b.text for b in response.content if b.type == "text"))

    updates = []
    for u in payload.get("updates", []):
        updates.append(IntelUpdate(
            # A code the model invented (not in the directory) counts as unmatched.
            customer_code=(u.get("customer_code") or "") if (u.get("customer_code") or "") in directory else "",
            customer_as_written=u.get("customer_as_written", ""),
            hooks=list(u.get("hooks", [])),
            source=source.value,
            raw_text=text.strip(),
            opportunity_groups=list(u.get("opportunity_groups", [])),
            referenced_products=list(u.get("referenced_products", [])),
            prior_incentive=u.get("prior_incentive", ""),
            relationship=u.get("relationship", "UNCHANGED"),
            next_contact=u.get("next_contact", ""),
            advice=u.get("advice", ""),
        ))
    return updates
