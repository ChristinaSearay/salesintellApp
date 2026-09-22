# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

POC sales-intelligence tool for jewellery wholesale reps: RFM scoring + an upsell engine over Unleashed ERP CSV exports, surfaced as one-page Markdown reports and a mobile-first web app with a rule-based learning loop. **README.md** covers setup, data layout, deployment (LAN/field use), and troubleshooting — this file does not repeat those.

## Commands

uv-managed, standard library plus the `anthropic` SDK (used only by `utils/summariser.py`). Use `uv` / `uv run`, never pip.

```bash
uv sync                            # create/refresh .venv
uv run python analyze.py           # RFM scorecard + upsell matching to stdout (writes nothing)
uv run python build_reports.py     # write reports/<code> - <name>.md for the 5 POC customers
uv run app                         # JSON API engine on :8000 (override with PORT)
cd frontend && pnpm dev            # rep UI (Next.js, v0 design) on :3000 — needs the engine
```

- **Reset a customer's learning:** delete `feedback/<code>.json`, or `POST /api/customer/<code>/reset`, or "Start over" in the UI.
- **No automated test suite or linter is configured.** Sanity-check changes by running `analyze.py` (the numbers) and the GUI. For a stable regression baseline run in CSV mode (`SEARAY_DATA_SOURCE=csv uv run python analyze.py`): the upsell join's known anchor there is My Jewellers (`MJ001`) with exactly 70 post-exclusion products created since its last order (27/03/2026). Live-mode numbers move with every sync, so don't diff those.

Project conventions (also enforced by `~/.claude/CLAUDE.md`): enums/config live in `constants/` (no raw string/int comparisons in logic); reusable logic in `utils/`; entry-point scripts stay thin; log behaviour changes in `CHANGELOG.md`.

## Architecture

Data (4 CSVs in `Example Data/`) → engine (`utils/`) → two outputs (Markdown reports **and** the web app), both driven by **one recommender**.

### `utils/recommend.py` is the single source of truth
Both `build_reports.py` and `server.py` get a customer's current top-3 from `current_actions(code)`. Two behaviours matter before editing:
- `_engine()` builds every `CustomerProfile` and candidate pool **once per process and caches them** → after changing profile/candidate/pool logic you must **restart `server.py`** to see the effect.
- Live intel (`utils/intel.py`, `notes/<code>.json`) is also read fresh every call: `effective_context(code)` layers summarised WhatsApp updates over `MEETING_NOTES` (hooks, opportunity groups, relationship flag, prior incentive); `recommend._live_candidates()` adds per-request candidates for new groups / requested terms and `_tilt_for_relationship()` re-weights on churn. The summariser (`utils/summariser.py`, Claude with a JSON-schema output, needs `ANTHROPIC_API_KEY`) only *proposes*; nothing is saved until the rep confirms in `/inbox`.
- The per-customer `PreferenceProfile` is loaded **fresh every call** from `feedback/<code>.json` → rep feedback takes effect immediately in the GUI, and in reports on the next `build_reports.py`. This is how learning "feeds back into reports."

### Customer scope
The app covers **every active customer** (completed order or invoice in the data) via `utils/customers.py:load_customers()`, sorted by 24-month spend. The five POC customers in `constants/customers.py` (`TARGET_CUSTOMERS`) keep curated names, manual balances, meeting notes and seed actions, and remain the scope of `analyze.py` / `build_reports.py` (pass codes to `build_profiles(codes)`); everyone else runs on the auto-generated candidates only.

### Needs-attention queue
`utils/attention.py` ranks every active customer for the accounts screen's top-5 queue: late against their own rhythm (average gap between distinct `order_dates`, deliberately not the median — order bursts drag a median to a few days), then no recent note, biggest spend first; any saved update in `notes/` within `NOTE_SNOOZE_DAYS` parks a customer at the back. Notes are read fresh per request (no restart needed).

### The rep playbook (ideas that travel)
`utils/playbook.py` is the second half of the learning loop: `preferences.py` learns from what a rep *rejects*, per customer; the playbook learns what a rep *did instead*, across customers. "I pitched my own idea" on a visit files an `Idea` against the situation it was used in — the customer's `Segment` plus their top `IDEA_GROUPS` bought groups — and `for_customer()` offers it to other customers in the same situation, as an `ActionKind.REP_IDEA` candidate carrying `Candidate.origin` ("Your idea from Leon Baker — same situation"). Similarity is deliberately narrow (same segment AND a shared group): a pitch that lands on an at-risk chain buyer is no evidence about a champion buying findings. Ideas join the pool in `_idea_candidates()` — per request, like live intel, so an idea saved on one visit is in play on the next with no restart. `confidence` is **global**: every rep's pitch/skip tap moves it, it scales the base score, and below `RETIRE_BELOW` an idea stops being offered to anyone new (it stays on the customer it was written for). Files live in `feedback/playbook/` so the deployed disk covers them without another env var.

### Muting an account ("do not alert again")
`utils/mute.py` holds accounts a rep asked never to be reminded about (shops often have two accounts — a buying-group one they rarely use and their own — so the quiet one is pure noise). A mute records the account's **last order date** at the time, stays in force while that is still their latest order, and lifts by itself (deleting the file) the moment a newer order lands in the sync — Christina's "settings revert back to normal". It is not a timer: unlike a note's `NOTE_SNOOZE_DAYS`, nothing expires. Muted customers get `AttentionReason.MUTED`, are filtered out of the queue and drop out of the overdue count; the customer's own page is the manual way back. Files live in `notes/mutes/` so the deployed persistent disk covers them without another env var (the `.json` scan in `utils/intel.py` skips the sub-directory).

### New customers from a visit
`utils/prospects.py` handles a business a rep visited that Unleashed doesn't have (Christina's process). `check()` compares the name against **every** Unleashed customer — `customer_rows()`, not `load_customers()`, because the whole point is shops with no order history — plus `utils/prospect_store.py`, which records what we created since the last sync. `create()` POSTs the bare-minimum Customer to Unleashed (`utils/unleashed.py:post`), saves it locally, and clears the directory cache so the customer exists in the app immediately instead of after the next `uv run sync`. Never make this automatic: the rep confirms, having seen the near-duplicates. A customer with no orders and no invoices gets `Segment.NEW_PROSPECT`, not "Hibernating / Lost".

### Recommendation pipeline (read these four together)
1. `utils/profile.py` — `CustomerProfile`: RFM scores + segment + relationship flag + bought groups + upsell matches, assembled from the 4 CSVs.
2. `utils/candidates.py` — the `Candidate` pool = curated seed actions (`constants/recommended_actions.py`) + auto-generated repeat-buying / upsell / white-space / range-extension / meeting-notes items (plus a "newest in a range they buy" top-up when the pool is below `MIN_AUTO_POOL`), each tagged with `kind`, `incentive_type`, `price_point`.
2b. `utils/repeat.py` — the buying rhythm behind the reorder cards. A `Cadence` (per product code or per group) uses the **median gap between distinct order dates**, so one bulk order can't invent a rhythm; thresholds live in `constants/repeat.py`. Two deliberate guards: only a line with ≥4 order dates can be framed as "they've stopped" (two orders is one gap, not a rhythm), and a thin history quiet for over a year is stale, not due.
3. `utils/preferences.py` — the learning. `apply_rejection()` maps a `RejectionReason` (`constants/feedback.py`) to deterministic effects (price ceiling, group exclusion, no-discounts, action-kind re-weighting). `rank_candidates()` scores the pool; **accepted candidates bypass all filters and are pinned to the top.**
4. `utils/recommend.py` — ranks, enforces group-diversity (max one card per product group in a shown set of 3), and serialises for the API.

### Renderer duck-typing
`utils/report.py:render()` consumes any object exposing `.title/.detail/.pitches/.groups/.incentive/.grounded_in`. Both the curated `Action` and the generated `Candidate` satisfy this, which is why reports can render either interchangeably.

### Data layer & the upsell join (`constants/config.py` `FileSpec` = per-file encoding + title-row offset; the files differ)
- File 1 Products → product master (code → Product Group).
- File 2 View Products → "new" products (`Created On`) + live stock, but has **no group** → joined to File 1 on code (`utils/products.py`).
- File 3 Sales Enquiry → orders: recency, frequency, the groups a customer already buys, and the per-order contact columns that feed the customer contact card (most recent order wins, per field; a synced `data/customers.json` overrides field-by-field when present).
- File 4 Invoice Enquiry → monetary (header-level totals only — no line items).
- Credit notes (Unleashed `CreditNotes` → `data/credits.json`, no CSV equivalent) → what the customer sent back, netted off monetary. `Total` is stored **positive**; `utils/profile.py` does the subtracting.
- "New since last order" = a product's `Created On` is after the customer's last order date.
- **Data source is pluggable** (`utils/datasource.py`): loaders read via `products_rows()`/`view_products_rows()`/`sales_rows()`/`invoice_rows()`/`customer_rows()`, returning the Unleashed sync cache (`data/*.json`, **the default since 04 Sep 2026, committed to the repo**) or CSV rows (`SEARAY_DATA_SOURCE=csv`). Same column-keyed shape either way, so the engine is source-agnostic — but the cache stores numbers as JSON numbers, so parsers must accept both (see `utils/parsing.py`). Unleashed client/sync live in `utils/unleashed*.py` + `uv run sync` (mappings verified against real API responses on 04 Sep 2026; refresh = sync, commit `data/`, push).

## Domain decisions baked in — intentional, do not "fix" as bugs
- **An "order" is Completed, Backordered or Placed** (`SalesStatus.COUNTED` in `constants/columns.py`) — all three are customer commitments, and backorders are where the big-ticket items sit. Parked is a draft/quote and stays out — unless it has been invoiced (`utils/orders.py:counts_as_order`, invoice matched by number SI-x ↔ SO-x): the team invoices straight off parked orders. The sync pulls every status so this policy can change without re-syncing; don't re-add an `orderStatus` filter to the API call.
- **Monetary = invoiced MINUS credit notes**, floored at zero (`constants/returns.py`). Credits run at ~21% of everything invoiced and over half on some accounts (Ori The Jeweller: $70.9k invoiced, $46.1k credited), so gross invoiced is not a usable number — it was inflating spend, M-scores and segments across 223 of 559 customers. Both credit types count: `Credit` returns stock against an invoice, `FreeCredit` credits without one, and both are money handed back. Only `CreditStatus.COUNTED` (Completed) counts — a Parked credit is an unapproved draft. Net spend can't go negative: a handful of customers returned goods invoiced *before* the 24-month window, which is a windowing artifact, not a debt. The CSV exports have no credit lines at all, so `SEARAY_DATA_SOURCE=csv` still reports gross — don't "fix" the resulting CSV/live gap.
- **Anchor date tracks the data source** (`ANCHOR_DATE` in `constants/config.py`): live Unleashed mode anchors on **today** (process start); CSV mode keeps the export snapshot **17 Jun 2026** — never a fixed date against live data (recency goes negative) and never wall-clock against the CSVs.
- **RFM uses absolute bands, not quintiles** (`constants/rfm.py`) — with only 5 customers, quintiles are meaningless.
- **Segment is objective RFM; the meeting-notes relationship flag annotates it, never overwrites** (e.g. Class A reads "Champion ⚠ churn risk").
- **A "gone quiet" flag is suppressed while the customer is ordering inside their own rhythm** (`constants/relationship.py` `QUIET_CLAIMS`, applied in `utils/relationship.py`). Flags are qualitative — a meeting note, or a WhatsApp update the summariser read — and go stale; order history doesn't. Gama read "Gone quiet on us" while placing a $58k order a fortnight earlier, because the thread was about a quote *we* owed them. CHURN_RISK and OCCASIONAL are deliberately exempt: a customer can order weekly and still be leaving (Class A does), and "orders as needed" describes how they buy rather than claiming they stopped. The flag isn't deleted from the note — it returns by itself once they actually go quiet. The three places that resolve a flag for display all go through `relationship.flag_for()`; the API re-reads notes per request (so a note saved mid-session applies without a restart), and that re-read must not bypass the guard.
- **Balance owing is a manual input** (`constants/customers.py`), not derivable from the exports.
- **`Misc` / `NON-STOCK ITEM` are excluded as noise**, and inconsistent group spellings are canonicalised (`constants/products.py:canonical_group`).
- **New-product pitches are in-stock first, with backorder split out.**

## Extending the intelligence
- New recommendation type → add a `Candidate` generator in `utils/candidates.py` (tag its `kind` / `incentive_type` / `price_point`).
- New rejection reason → add to `RejectionReason` in `constants/feedback.py` and its effect in `preferences.apply_rejection()`.
- Per-customer curated actions are structured data in `constants/recommended_actions.py` (these become the high-priority seeds in the pool).

## Rep UI — Next.js frontend (`frontend/`)
The rep UI is a Next.js (App Router · JSX · Tailwind · shadcn) app on **:3000** with v0's design. It does NOT replace the backend: the Python engine stays the brain and serves the **API only** on :8000 (the old `webapp/` built-in UI was removed — `server.py` no longer serves static files). `frontend/next.config.mjs` proxies `/api/*` → `:8000`, and `frontend/src/lib/api.js` adapts the raw API into the view model the UI binds to (same shape as `V0_PROMPT.md`). Run both: `uv run app` (engine) + `cd frontend && pnpm dev`. Workflow in `frontend/V0_WORKFLOW.md`.
