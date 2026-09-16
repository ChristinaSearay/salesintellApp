# Changelog

## 2026-09-16 (2)

### Added
- Item-level recommendations driven by each customer's own buying rhythm (`utils/repeat.py`, `constants/repeat.py`): **"Due to reorder"** (a product code they repurchase, overdue against the median gap between their order dates, in stock now), **"Time to restock <group>"** (a range they buy on a rhythm that has gone visibly quiet), and **"Extend their range"** (an in-stock piece in the same group and price band as one of their best sellers, never ordered).
- `ActionKind.REORDER` (base score 72, above Upsell) with the "Due to reorder" label in the rep UI.
- `CustomerProfile.purchases` — real product lines (noise excluded) behind the cadence analysis.

### Fixed
- The five POC customers are always in the customer directory, even once they age out of the 24-month window (The Cut has: 0 rows in the 16 Sep sync), so their reports still generate and their visit pages still load.

## 2026-09-16

### Added
- All active Unleashed customers (anyone with a completed order or invoice in the 24-month window — 567 on the 4 Sep sync) are in the app, each with RFM, contact card and pitches (`utils/customers.py:load_customers`).
- Accounts screen search by customer name or code; shows the top 30 by spend until you search; each card shows 2-year spend and last order.
- `uv run sync` now stores the customer name from the Customers endpoint (`CustomerCol.NAME`).
- "Newest in a range they buy" pitches: when a customer's candidate pool is thin (frequent buyers with nothing new since their last order), it is topped up with the newest in-stock item per bought group that they have never ordered.

### Changed
- `GET /api/customers` returns lean account cards for every active customer, biggest spend first; customer/intel endpoints accept any active customer code.
- WhatsApp summariser matches against every active customer; unknown codes it returns are treated as unmatched.
- `build_profiles()` takes optional customer codes; `analyze.py` and `build_reports.py` stay scoped to the five POC customers.
- `TargetCustomer` renamed to `Customer`; balance owing defaults to 0 outside the POC five.

## 2026-09-04

### Changed
- Live Unleashed data is now the default data source (`SEARAY_DATA_SOURCE` defaults to `unleashed`; set `csv` for the snapshot exports). The sync cache `data/*.json` is committed so deployed copies have it — refresh with `uv run sync`, commit, push.
- Anchor date now tracks the data source: today in live mode, the 17 Jun 2026 snapshot in CSV mode (`CSV_SNAPSHOT_DATE`).

### Added
- Customer contact card (contact name · phone · email) under the company name on the visit page, in the API (`customer_summary.contact`) and in the Markdown report header — derived from the Unleashed sales export's per-order contact columns (most recent order wins, per field).
- `uv run sync` now also pulls the Unleashed Customers endpoint into `data/customers.json` (`CustomerCol`, mappings marked VERIFY); when present it overrides the order-row contact field-by-field, preferring mobile over landline.

### Fixed
- `parse_money`/`parse_number` accept JSON numbers, so the engine runs on the Unleashed sync cache (first live sync stored numeric fields as numbers, not strings).
- AU mobiles stored in Unleashed without their leading 0 (e.g. `437447787`) are normalised to `0437 447 787` for display and tel: links (`utils/parsing.py:normalise_phone`).

## 2026-08-30

### Added
- WhatsApp intel loop: paste a team-chat dump in the new `/inbox` screen → Claude summarises it into per-customer updates (customer match incl. "not one of ours", hooks, product groups to pitch, terms asked for, relationship signal, next move) → rep confirms → saved to `notes/<code>.json` (`utils/intel.py`, `utils/summariser.py`, `constants/intel.py`).
- Saved updates feed "What's going on" (live bullets first, tagged 💬, with a "Suggested next move" line), the relationship flag, the Markdown reports, and the pitch set: new opportunity candidates for groups raised in chat, a "Respond to the terms they asked for" action when a deal was requested, and a retention tilt when the update flags churn.
- API: `POST /api/intel/summarise`, `GET/POST /api/intel/<code>`, `POST /api/intel/<code>/delete`; `ANTHROPIC_API_KEY` / `SEARAY_INTEL_MODEL` / `SEARAY_NOTES_DIR` env vars; "💬 WhatsApp" entry on the accounts screen and an updates link on each visit page.

### Changed
- `anthropic` SDK added as the one third-party dependency (summariser only; engine stays stdlib).
- Profiles and candidate pools read meeting-notes context via `utils.intel.effective_context()` instead of `MEETING_NOTES` directly.

## 2026-06-19

### Removed
- Built-in `webapp/` UI and its static-file serving in `server.py` — port 8000 is now **JSON-API-only** (its root returns a small pointer to the Next.js UI). The rep UI is the Next.js frontend on :3000.

### Changed
- `Example Data/` (the CSV exports) is now committed so the deployed backend has data — **keep the repo private** (it holds real customer/sales data); only the Unleashed sync cache (`data/`) stays gitignored.
- Integrated v0's UI design into `frontend/` (warm-ivory "Lustre" theme, champagne-gold accent, Fraunces serif, framer-motion; redesigned `AccountCard`/`Pitch`, `globals.css`, `layout.js`) and wired it to the **live** engine — real reason names, real pitches, and the accept/skip → re-suggest learning loop (`api.js` `toAccount` now emits v0's `status`/`tone` shape). v0's mock `data.js`/`pitchPool` dropped in favour of `api.getPrep`/`sendFeedback`/`reset`.

### Added
- Unleashed API integration (scaffold) — HMAC-signed paginated client (`utils/unleashed.py`), a sync that maps API objects into the engine's row shape and caches them in `data/` (`utils/unleashed_sync.py`, `uv run sync`), and a pluggable data source (`utils/datasource.py`) switched by `SEARAY_DATA_SOURCE=csv|unleashed`. Engine loaders read through it; **CSV stays the default and unchanged**. Field mappings marked `VERIFY` pending live credentials.
- `/healthz` endpoint (returns `{"ok": true}`) for platform health checks; `SEARAY_FEEDBACK_DIR` env var to store learned preferences on a persistent disk (e.g. a Render disk).
- Local `.env` auto-loading (tiny stdlib loader in `constants/__init__.py`) + `.env.example` — secrets/config in `.env` are picked up by every `uv run` (real shell env vars still win); `.env` is gitignored.
- `uv run dev` — one command that starts both the API engine (:8000) and the Next.js UI (:3000) together, and stops both on Ctrl+C (`dev.py`, `[project.scripts] dev`).
- `frontend/` two-screen flow wired to the live engine: Accounts list (`src/app/page.js`, `AccountCard`) → Visit prep (`src/app/visit/[code]/page.js`, `Pitch`) with the full accept/reject → re-suggest learning loop in React via `src/lib/api.js`.
- `frontend/` — Next.js (App Router · JSX · Tailwind · shadcn-ready) rep UI scaffold for designing in v0. Proxies `/api/*` to the Python engine (`next.config.mjs`) and adapts responses into a plain-language view model (`src/lib/api.js`); verified end-to-end (Next :3000 → Python :8000). Plus `V0_PROMPT.md` (ready-to-paste v0 prompt) and `frontend/V0_WORKFLOW.md`.
- `uv run app` — frees port 8000 if occupied, then starts the rep web app (`app.py`, `utils/port.py`, `[project.scripts]` entry point).

### Fixed
- `frontend/src/app/globals.css` forced to a light theme — create-next-app's `prefers-color-scheme: dark` block turned inherited text near-white on the light UI (unreadable).
- `server.py` prints a clear message when port 8000 is already in use, with steps to stop the old process or pick another port.

### Added
- Rep app "Before you walk in" story panel — plain-English status (segment/risk translated out of RFM jargon), the meeting-note signals, and key facts (spend, last order, usual categories) so a non-technical rep knows the context at a glance (`customer_summary` now returns `hooks`/`next_contact`/`spend`/`orders`/`last_order_days`).
- CLAUDE.md — guidance for future Claude Code sessions: commands plus the big-picture architecture (shared recommender, learning pipeline) and the intentional domain decisions.
- README.md — project overview, quick start, data setup, deployment (LAN/field use), development conventions, and troubleshooting.
- uv project config (`pyproject.toml`) — project is now uv-managed (standard library only, no third-party deps).
- Mobile-first rep GUI (`webapp/`) served by a zero-dependency stdlib server (`server.py`): tap 👍/👎 per action, pick reason chips on rejection, get 3 better — with a "what I've learned" strip and deep-linking (`/#c=CODE`).
- Rule-based rejection → re-suggestion learning loop: tagged candidate pool (`utils/candidates.py`), per-customer preference model persisted to `feedback/<code>.json` (`utils/preferences.py`), and a shared recommender (`utils/recommend.py`).
- Reason→effect rules: price ceiling, group exclusion, no-discounts, low-pressure (kind re-weighting); accepted actions are pinned and bypass filters; group-diversity in each shown set.
- Learned preferences feed back into the one-page reports (`build_reports.py` now pulls the live top-3 from the recommender).
- `constants/` layer: config (anchor date, per-file encoding/header specs), target customers, column names, RFM bands/segments/relationship flags, product-group rules, structured meeting notes, and per-customer recommended actions.
- `utils/` layer: CSV loaders (per-file encoding + title-row handling), date/money parsers, RFM scoring + segment assignment, product-master/catalogue loaders, and the upsell-matching engine.
- `analyze.py`: Step 2+3 checkpoint — prints RFM scorecard and per-customer product matching.
- `build_reports.py` + `utils/report.py`: Step 4 — generates one-page Markdown sales action reports for the 5 target customers in `reports/`.
- RFM scoring with absolute (non-quintile) bands; segments annotated with a meeting-notes relationship flag.
- Upsell engine: new-since-last-order products (in-stock first, backorder split) inside bought groups, plus white-space groups; product codes resolved live to descriptions/prices.
- Each report's 3 recommended actions name real product groups/codes/prices and flag any proposed incentive as pending head-office approval; includes a rep-feedback stub for the future interactive tool.

### Changed
- Redesigned the rep web app — premium visual design (emerald/gold, serif wordmark, soft depth, large touch targets), plain-language status throughout (no RFM/segment jargon), and a clearer "accounts → prep visit → 3 pitches → keep/swap" flow.
- Adopt `uv` for Python package/environment management; run scripts via `uv run python <script>` (e.g. `uv run python server.py`, `uv run python build_reports.py`) instead of `python3`/`pip`.
