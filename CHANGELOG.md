# Changelog

## 2026-06-19

### Removed
- Built-in `webapp/` UI and its static-file serving in `server.py` — port 8000 is now **JSON-API-only** (its root returns a small pointer to the Next.js UI). The rep UI is the Next.js frontend on :3000.

### Changed
- Integrated v0's UI design into `frontend/` (warm-ivory "Lustre" theme, champagne-gold accent, Fraunces serif, framer-motion; redesigned `AccountCard`/`Pitch`, `globals.css`, `layout.js`) and wired it to the **live** engine — real reason names, real pitches, and the accept/skip → re-suggest learning loop (`api.js` `toAccount` now emits v0's `status`/`tone` shape). v0's mock `data.js`/`pitchPool` dropped in favour of `api.getPrep`/`sendFeedback`/`reset`.

### Added
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
