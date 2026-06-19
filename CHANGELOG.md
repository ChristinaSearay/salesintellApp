# Changelog

## 2026-06-19

### Fixed
- `server.py` prints a clear message when port 8000 is already in use, with steps to stop the old process or pick another port.

### Added
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
- Adopt `uv` for Python package/environment management; run scripts via `uv run python <script>` (e.g. `uv run python server.py`, `uv run python build_reports.py`) instead of `python3`/`pip`.
