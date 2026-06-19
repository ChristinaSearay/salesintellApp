# Changelog

## 2026-06-19

### Added
- `constants/` layer: config (anchor date, per-file encoding/header specs), target customers, column names, RFM bands/segments/relationship flags, product-group rules, structured meeting notes, and per-customer recommended actions.
- `utils/` layer: CSV loaders (per-file encoding + title-row handling), date/money parsers, RFM scoring + segment assignment, product-master/catalogue loaders, and the upsell-matching engine.
- `analyze.py`: Step 2+3 checkpoint — prints RFM scorecard and per-customer product matching.
- `build_reports.py` + `utils/report.py`: Step 4 — generates one-page Markdown sales action reports for the 5 target customers in `reports/`.
- RFM scoring with absolute (non-quintile) bands; segments annotated with a meeting-notes relationship flag.
- Upsell engine: new-since-last-order products (in-stock first, backorder split) inside bought groups, plus white-space groups; product codes resolved live to descriptions/prices.
- Each report's 3 recommended actions name real product groups/codes/prices and flag any proposed incentive as pending head-office approval; includes a rep-feedback stub for the future interactive tool.
