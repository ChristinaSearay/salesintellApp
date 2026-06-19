# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

POC sales-intelligence tool for jewellery wholesale reps: RFM scoring + an upsell engine over Unleashed ERP CSV exports, surfaced as one-page Markdown reports and a mobile-first web app with a rule-based learning loop. **README.md** covers setup, data layout, deployment (LAN/field use), and troubleshooting — this file does not repeat those.

## Commands

uv-managed, **standard library only** (no third-party deps). Use `uv` / `uv run`, never pip.

```bash
uv sync                            # create/refresh .venv
uv run python analyze.py           # RFM scorecard + upsell matching to stdout (writes nothing)
uv run python build_reports.py     # write reports/<code> - <name>.md for all 5 customers
uv run app                         # JSON API engine on :8000 (override with PORT)
cd frontend && pnpm dev            # rep UI (Next.js, v0 design) on :3000 — needs the engine
```

- **Reset a customer's learning:** delete `feedback/<code>.json`, or `POST /api/customer/<code>/reset`, or "Start over" in the UI.
- **No automated test suite or linter is configured.** Sanity-check changes by running `analyze.py` (the numbers) and the GUI. The upsell join has a known anchor: My Jewellers (`MJ001`) has exactly 74 products created since its last order (27/03/2026) — a good regression check.

Project conventions (also enforced by `~/.claude/CLAUDE.md`): enums/config live in `constants/` (no raw string/int comparisons in logic); reusable logic in `utils/`; entry-point scripts stay thin; log behaviour changes in `CHANGELOG.md`.

## Architecture

Data (4 CSVs in `Example Data/`) → engine (`utils/`) → two outputs (Markdown reports **and** the web app), both driven by **one recommender**.

### `utils/recommend.py` is the single source of truth
Both `build_reports.py` and `server.py` get a customer's current top-3 from `current_actions(code)`. Two behaviours matter before editing:
- `_engine()` builds every `CustomerProfile` and candidate pool **once per process and caches them** → after changing profile/candidate/pool logic you must **restart `server.py`** to see the effect.
- The per-customer `PreferenceProfile` is loaded **fresh every call** from `feedback/<code>.json` → rep feedback takes effect immediately in the GUI, and in reports on the next `build_reports.py`. This is how learning "feeds back into reports."

### Recommendation pipeline (read these four together)
1. `utils/profile.py` — `CustomerProfile`: RFM scores + segment + relationship flag + bought groups + upsell matches, assembled from the 4 CSVs.
2. `utils/candidates.py` — the `Candidate` pool = curated seed actions (`constants/recommended_actions.py`) + auto-generated upsell / white-space / meeting-notes items, each tagged with `kind`, `incentive_type`, `price_point`.
3. `utils/preferences.py` — the learning. `apply_rejection()` maps a `RejectionReason` (`constants/feedback.py`) to deterministic effects (price ceiling, group exclusion, no-discounts, action-kind re-weighting). `rank_candidates()` scores the pool; **accepted candidates bypass all filters and are pinned to the top.**
4. `utils/recommend.py` — ranks, enforces group-diversity (max one card per product group in a shown set of 3), and serialises for the API.

### Renderer duck-typing
`utils/report.py:render()` consumes any object exposing `.title/.detail/.pitches/.groups/.incentive/.grounded_in`. Both the curated `Action` and the generated `Candidate` satisfy this, which is why reports can render either interchangeably.

### Data layer & the upsell join (`constants/config.py` `FileSpec` = per-file encoding + title-row offset; the files differ)
- File 1 Products → product master (code → Product Group).
- File 2 View Products → "new" products (`Created On`) + live stock, but has **no group** → joined to File 1 on code (`utils/products.py`).
- File 3 Sales Enquiry → orders: recency, frequency, and the groups a customer already buys.
- File 4 Invoice Enquiry → monetary (header-level totals only — no line items).
- "New since last order" = a product's `Created On` is after the customer's last order date.

## Domain decisions baked in — intentional, do not "fix" as bugs
- **Monetary = gross invoiced.** The invoice export contains no returns/credit lines, so it overstates retained revenue; reports flag consignment customers (e.g. My Jewellers). Do not assume returns exist in the data.
- **Anchor date = 17 Jun 2026** (`ANCHOR_DATE` in `constants/config.py`), the export snapshot — recency is measured from it, not wall-clock time.
- **RFM uses absolute bands, not quintiles** (`constants/rfm.py`) — with only 5 customers, quintiles are meaningless.
- **Segment is objective RFM; the meeting-notes relationship flag annotates it, never overwrites** (e.g. Class A reads "Champion ⚠ churn risk").
- **Balance owing is a manual input** (`constants/customers.py`), not derivable from the exports.
- **`Misc` / `NON-STOCK ITEM` are excluded as noise**, and inconsistent group spellings are canonicalised (`constants/products.py:canonical_group`).
- **New-product pitches are in-stock first, with backorder split out.**

## Extending the intelligence
- New recommendation type → add a `Candidate` generator in `utils/candidates.py` (tag its `kind` / `incentive_type` / `price_point`).
- New rejection reason → add to `RejectionReason` in `constants/feedback.py` and its effect in `preferences.apply_rejection()`.
- Per-customer curated actions are structured data in `constants/recommended_actions.py` (these become the high-priority seeds in the pool).

## Rep UI — Next.js frontend (`frontend/`)
The rep UI is a Next.js (App Router · JSX · Tailwind · shadcn) app on **:3000** with v0's design. It does NOT replace the backend: the Python engine stays the brain and serves the **API only** on :8000 (the old `webapp/` built-in UI was removed — `server.py` no longer serves static files). `frontend/next.config.mjs` proxies `/api/*` → `:8000`, and `frontend/src/lib/api.js` adapts the raw API into the view model the UI binds to (same shape as `V0_PROMPT.md`). Run both: `uv run app` (engine) + `cd frontend && pnpm dev`. Workflow in `frontend/V0_WORKFLOW.md`.
