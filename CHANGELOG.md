# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

## [Unreleased]

### Fixed (v0.1.9 — staff sample figures, 12 Nov 2026)
- Staff Sales shows permission-filtered recorded lead statuses for the selected Company and period. Qualification/conversion remain unset.
- Add a single staging finance-demo population script with ledger and staff-source checks and correctly scoped report links.

### Changed (v0.1.7 — Somaliland regional settings, 12 Nov 2026)
- Sidra settings, demo Companies and native setup presets use Somaliland. Create its Country master before assigning links; retain USD, DD/MM/YYYY and Africa/Mogadishu.
- Migration updates existing site defaults, Company/Address country links, the native territory and address template. Existing contracts, vouchers and customer identities are preserved. Other country selections and the upstream country catalogue remain available.

### Fixed (v0.1.6 — Desk usability)
- Consistent sidebar ownership, construction/collections/report links and count-chart formatting.
- Scheme connections and permission-filtered counts, clearer identifiers, unit list columns and house-only fields.
- Staff-facing labels without requirement codes, readable schedule columns, map fallback and import template download.
- Missing asking prices are explicit; no prices, signed terms, legal wording or financial rules are invented.


### Fixed (v0.1.5 — staff dashboard review fixes, 12 Nov 2026)
- Sidra Project Manager and Sidra Inspector no longer get a permission error on the staff dashboard: unit, contract, reservation and schedule groups their role cannot read are returned as null/empty (unknown, not zero).
- Staff dashboard money is summed as exact decimals; a missing or invalid amount makes the total null instead of being counted as zero.
- The schedule bucket "Next 30 days" now covers tomorrow through day 30, the same window as the executive `due_next_30_days`; rows due today have a separate "Due today" bucket.
- Overdue milestones use the shared `stage_overdue` rule (no actual end, completion below 100, active/on-hold jobs only), consistent with the executive stage exceptions.
- Open spec questions, not changed here: the two contract-value totals and the construction progress % (GitHub issues labelled `spec-question`).

### Added (v0.1.4 — collections rules as profile settings, decision G9, issue #3, 12 Nov 2026)
- Sidra Contract Profile: eleven new settings for the rules the installment engine had to assume: days before a per-day penalty starts, cap basis, whether payment on the last notice day is late, what a receipt pays first, how a payment beyond what is due is allocated, days before an installment counts as missed, what "one installment" means for the refund, whether penalties paid are in the refund base, and Profile B's title part month, refund-right start and compensation base
- The same settings on Sidra Sale Contract: frozen from the profile on generated contracts, prefilled and editable on registered (External) contracts, kept in the terms snapshot (INS-20). Stored only; nothing is applied (`CLAUDE.md` rule 3)
- Profiles A and B seeded with the engine's assumptions (AT-06 to AT-13); title rules the engine left open are "Pending Decision". Patch `v0_4.set_collection_rule_defaults` fills only blank settings on existing profiles; contracts are not changed
- `docs/DECISIONS-AND-GATES_v0.1.md`: G9 (issue #3) and G10 (issue #8: bilingual clauses, wording supplied by Sidra)

### Added (v0.1.3 — isolated fictional financial data, 9 Nov 2026)
- Administrator-only, staging-opt-in finance demo loader: a separate fictional Company, six demo accounts, ten submitted native ERPNext vouchers, private ownership manifest, read-only balance verification and repeat protection. Never adopts an existing Company, duplicates vouchers or changes production posting rules.
- Native GL, Trial Balance, P&L, Balance Sheet and receivable/payable reports can show real posted fictional data. Demo-only dashboard receipts/aging read permission-filtered native records and explicitly label invoice arrears separately from contract schedules.
- Reuses external contract registration with a private fictional original and three installments, available plots, leads and one recorded milestone exception. No contract document generation or construction module expansion.

### Added (v0.1.2 — read-only executive dashboard, 8 Nov 2026)
- Codex takes over the remaining dashboard backend/client implementation and tests end to end under the user's updated allocation; financial/legal gates are unchanged.
- Management-only executive snapshot on the existing staff endpoint: permission-filtered signed sales and trends, available units/verified asking prices, gross scheduled rows tomorrow through day 30, current stage date exceptions, expired active reservations and registration-age exposure. Reuses the reviewed Insights source definitions without installing another app or executing unrestricted parent SQL.
- Native **Sidra Executive Detail** Script Report provides independently authorized source rows and parent links; Company/Unit User Permissions, role restrictions, date/currency consistency, whole-contract exclusions and stale-date/project rejection are enforced server-side. No financial records or workflow states are changed.
- Gross schedules are labelled separately from unpaid balances/forecast cash. Unavailable receipt/allocation, target and approved-baseline sources remain unavailable. Reporting periods have exact inclusive 30/90-day windows in Africa/Mogadishu; signed sales and operational schedule aggregates exclude future-signed/foreign-currency contracts.

### Added (staff clients backend: locations, dashboard and staff page)
- `/sidra-staff/` (`www/sidra-staff/`): Codex's staff UI on the site's own origin for signed-in Sidra staff (guests go to login), session CSRF token injected per request into `window.SIDRA_CONFIG`, not cached; UI files published at `/assets/sidra_realestate/staff/` through the `public/staff` link to `clients/staff/web`
- `sidra_realestate/api/staff_dashboard.py`: `get_dashboard` (schema_version 1 of API-CONTRACT.md), permission-filtered through `frappe.get_list`, one Company and currency, money as decimal strings; payments and sales pipeline returned as unavailable with a reason (no receipts in ERPNext yet; no lead stages), scheduled amounts labelled as obligations; jobs from recorded stages only
- `sidra_realestate/api/locations.py` and `location_geometry.py`: Codex's plot / site location adapter, reviewed and integrated (`get_location`, `set_location` with stale-edit refusal, `export_kml`); `sidra_location` Geolocation field added to Sidra Unit and Sidra Construction Job (existing GPS text kept); integration tests with real Sidra roles

### Added (sample migration data and brokerage spec)
- `docs/samples/SAMPLE-LIVE-CONTRACTS_v0.1.csv` (also `/assets/sidra_realestate/templates/sample_live_contracts.csv`): 8 synthetic live contracts, 182 schedule rows (12 to 36 months, both down-payment modes, a fee row, a two-plot contract); the demo adds free plots DEMO-M-001 to 009 for it, and `tests/test_demo.py` imports it
- `docs/BROKERAGE_v0.1.md`: draft spec for approval: Sidra as broker for owners' plots and agent commission on Sidra's sales, 2.5 % of the plot price, due in full on the buyer's first payment, recorded not posted; acceptance tests BR-01 to BR-10

### Changed (docs)
- `docs/DEPLOYMENT_v0.1.md`: test VPS status, lessons from the first deployment (IPv6, private home folders and nginx, default site, tmux, deploy key), D4 and contract capture patches, Module Profile for staff

### Added (import capability, decision G5)
- **Sidra Contract Import** (Real Estate → Contract Import): upload a CSV or XLSX of live contracts, one row per schedule line; **Validate** runs every contract check and keeps nothing; **Import** creates draft registered contracts, all or nothing; references already registered for the Company are skipped; optional creation of missing customers. Template: `public/templates/sidra_contract_import_template.csv`. Payments to date are not imported (D8)
- `services/contract_import.py` (pure reader: DD/MM/YYYY and ISO dates, row-numbered errors) with pure tests

### Added (white-label and navigation, Mohamoud 7 Nov 2026)
- Sidra Homes branding: system and website name, navbar logo, favicon, login splash, website footer; contract print and README carry the official Sidra Homes logo (`sidra_realestate/branding.py`; `public/images/sidra-logo.png`, `sidra-icon.png`, `favicon.png`)
- One "Sidra Homes" app on the apps screen and rail with two sections from shipped Dock / Sidebar records: **Real Estate** (schemes, plots, reservations, price history, sale contracts, profiles, clauses, contract settings, customers) and **Construction** (construction jobs, customers)
- Module Profile "Sidra Staff" hides Manufacturing, Stock, Projects, Buying, Quality, Support, Assets, Subcontracting and Maintenance for staff (hidden, not deleted); demo users get it

### Added (contract capture: docs/CONTRACT-CAPTURE_v0.3.md, decisions D1–D7, issue #13)
- Register contracts prepared outside the system: `Sidra Sale Contract.source` (External (registered), the default, or Generated from profile), external reference unique per Company among confirmed contracts (transaction-safe key), original signed contract attachment, captured terms, terms summary
- Actual schedules entered row by row (Installment / Down payment / Fee, same-day and past dates allowed); Fill Schedule (`propose_schedule`) proposes rows only when asked and replaces only after confirmation
- Reconciliation: schedule total, amount due and difference (D1 down payment mode, D2 fee rows); confirmation within the Contract Settings tolerance ($5.00, D3) after acknowledgement, stored in the snapshot
- D5: External confirmation needs only the original document and validates signing data where present; Generated contracts keep the full gate
- D6: penalty, default and title terms captured on the contract (profile range checks reused), frozen at confirmation, never applied
- D7: `terms_approved_by` / `terms_approved_on` and the same in the snapshot
- `Sidra Contract Settings` (schedule tolerance); print shows "Registered copy of an external contract" and row types
- Patch `v0_3.set_contract_source`: existing installment contracts become Generated, rows typed Installment, totals back-filled

### Added (decisions of 7 Nov 2026)
- `docs/DECISIONS-AND-GATES_v0.1.md`: G1 configurable installment terms (12–36 months and between), G2 penalties as a waiting period plus an amount, G3 no Murabaha, G4 ERPNext as the only ledger, G5 import capability now and migration later, G6 merge on green CI, G7 Codex continues when Claude Code's limit is reached, G8 zip removed
- `AGENTS.md` for Codex, pointing to `CLAUDE.md`

### Removed
- `sidra-erp_v0.1.0.zip`, committed by mistake

### Changed (decision D4, issue #13: code)
- Profile B is seeded with a 20-day title deadline and no legal hold (`install.py`); the 14 days in Contract B is a typo
- Patch `v0_3.resolve_profile_b_title_deadline`: on existing sites, changes Profile B only while it still has the seeded hold values (legal hold on, deadline 0), sets 20 days, lifts the hold and adds a Comment citing issue #13; a profile already edited by management is left alone. Saved contracts keep their frozen terms (INS-20)
- Tests: the legal-hold mechanism is now tested on a held copy of Profile B (`tests.helpers.make_held_profile`); new tests for the D4 seed, the patch (seeded, edited, run twice) and a Profile B contract submitting with the AT-03 schedule

### Changed (decision D4, issue #13)
- `CLAUDE.md` rule 3 and `docs/SREMS-SRS_v2.0-DRAFT.md` (§1.4, §3.3 Profile B, §9 item 1) record that Contract B's title deadline is 20 days and that Profile B's legal hold is lifted only through the D4 seed / patch; rule 3 also records D7 for registered contracts
- Roles: Claude Code implements, including the contract capture brief; the Codex role and Task 0 in `docs/CONTRACT-CAPTURE_v0.3.md` are superseded (Mohamoud, 7 Nov 2026) Docs only: the seed and patch in `docs/CONTRACT-CAPTURE_v0.3.md` are not part of this change

### Fixed (ChatGPT review of develop @ cbce4f3)
- Signed copy: must be a private file attached to this contract's Signed Copy field, on disk, readable by the submitter and used by no other record; a pasted or re-used file URL is refused
- Lock order: units are locked first (ascending name), then reservations, in reserve, cancel, expiry and contract submit
- Notary reference: whitespace removed; `notary_reference_key` with a database unique index is set at submit, so concurrent submissions cannot share a reference; drafts may share one
- Unit scheme moves: refused across Companies when the unit has reservations, contracts or price history, and refused entirely once on a signed contract
- Clause approval is checked against the library at submit; changed wording needs Revise Draft (docs/CONTRACT-REVISION_v0.1.md, issue #11); signed snapshots never change
- Money fields named "USD" as a currency field, so amounts showed in the site default currency (INR on a bare site); they now use the Company's currency
- Profile B's legal hold is reported before missing signing data

### Added
- Reserve Unit and Cancel Reservation actions on the unit form, Cancel Reservation on the reservation form, Revise Draft on draft contracts
- Role profiles pairing each Sidra role with the ERPNext role its screens need (sales staff could not look up a Customer with Sidra roles alone)
- `site_setup.apply_regional_settings` (NFR-10: USD, DD/MM/YYYY, Africa/Mogadishu)
- `demo.create_demo_data` / `demo.export_pdfs` for private staging (guarded by `sidra_allow_demo_data`)
- Contract print format uses the Chrome PDF generator; real PDF output tested
- Patches `v0_2.set_notary_reference_keys`, `v0_2.set_document_currency`
- docs/DEPLOYMENT_v0.1.md, docs/CONTRACT-REVISION_v0.1.md; traceability CSV gains implementation status, PR and test evidence columns

### Added
- `docs/SREMS-SRS_v2.0-DRAFT.md` — ERPNext implementation specification from ChatGPT; working spec from 5 Nov 2026, with a repository note (repo `sidra-erp`, app `sidra_realestate`)
- `docs/REQUIREMENTS-TRACEABILITY_v2.0-DRAFT.csv` — requirement ID to phase and status map
- `docs/CLAUDE-CODE-HANDOFF_v2.0.md` — implementation handoff, first-PR checklist, subsequent PRs, PR template
- `docs/ENVIRONMENT_v0.1.md` — pinned versions: Frappe v16.55.2, ERPNext v16.53.0, Python 3.14, Node 24, MariaDB 11.8
- `.github/pull_request_template.md` — the handoff's PR template

- P0 prototype (SRS v2.0 §4): 10 DocTypes — Sidra Scheme, Sidra Unit, Sidra Reservation, Sidra Contract Profile, Sidra Contract Unit, Sidra Sale Contract, Sidra Installment Line, Sidra Construction Job, Sidra Project Stage, Sidra BOQ Line
- `services/reservations.py`: `reserve_unit` / `cancel_reservation` (row-locked, Sales roles only) and the daily `expire_reservations` job
- `services/schedule.py`: pure-Python installment generator (whole-dollar rounding, last installment absorbs the rest, grace months, due day 1–28)
- Profile A and Profile B created on install and migrate when missing; Profile B on legal hold (14 vs 20-day title deadline)
- Roles fixture: Sidra Sales User, Sales Manager, Project Manager, Inspector, Finance Reviewer, General Manager
- Integration tests for every DocType, including concurrent reservation; pure tests for the schedule (AT-01 to AT-04)
- CI job that builds an ERPNext v16 bench (Frappe v16.55.2, ERPNext v16.53.0, MariaDB 11.8), installs, migrates, builds and runs the tests

- Unit price history (SAL-02): submittable `Sidra Unit Price History`; new prices must take effect after the latest one; only future-dated entries can be cancelled; `Sidra Unit.cash_price` mirrors today's price and is refreshed daily; a unit created or imported with a price gets an "Initial price" entry
- Bulk import (SAL-01): Data Import enabled for Sidra Scheme, Sidra Unit and Sidra Unit Price History (Sales Manager)
- Patch `v0_2.create_initial_unit_prices`: back-fills history for units priced before this change

- Contract parties (SAL-19): child table Sidra Contract Party (Seller, Seller Guarantor with pledged property, Witness) on Sidra Sale Contract
- Clause library (SAL-20): Sidra Contract Clause with Somali and English wording, approved only by the General Manager; profiles list their clauses; a contract freezes them with its terms (INS-20, INS-21). Five clauses seeded with no wording and not attached to any profile (issue #8)
- Signed-copy gate: a contract submits only with a private signed copy, notary name and unique reference, one Seller, a Seller Guarantor with pledged property, two Witnesses with phones and approved wording for every clause
- Print format "Sidra Sale Contract" (default): units with boundaries, price, schedule, clauses in Somali and English, parties with signature lines, notary

### Changed
- `reserve_unit`, `cancel_reservation` and price entries now enforce per-Company user permissions on the unit
- `CLAUDE.md` points at SRS v2.0-DRAFT and adds the P0 prototype boundary (no postings, refunds, penalties, title transfer or overrides; Profile B legal hold)

## [0.1.1] — 2026-11-05

### Added
- `docs/HANDOVER_v1.0.md` — handover to Claude Code: roles (ChatGPT architecture / QA, Claude Code implementation), rules, fixed decisions, contract profiles A / B, phase plan, acceptance cases AT-01 to AT-13, first tasks
- `CLAUDE.md` — standing instructions loaded by Claude Code

### Changed
- Roadmap follows the agreed phase order: Foundation, Property, Sales, Collections, Construction, Finance, Release

## [0.1.0] — 2026-11-05

### Added
- Frappe app skeleton for ERPNext v16: `hooks.py`, `modules.txt`, `patches.txt`, `pyproject.toml`
- Five modules: Sidra Property, Sidra Sales, Sidra Installments, Sidra Construction, Sidra Brokerage
- `docs/SREMS-SRS_v1.6.md` — requirements specification v1.6
- `docs/ERPNEXT-MAPPING_v0.1.md` — mapping of every requirement to ERPNext standard features or custom DocTypes
- GitHub Actions CI: ruff lint and Python syntax check

