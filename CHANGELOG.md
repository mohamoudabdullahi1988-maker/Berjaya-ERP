# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

## [Unreleased]

### Added (white-label and navigation, Mohamoud 7 Nov 2026)
- Sidra Homes branding: system and website name, navbar logo, favicon, login splash, website footer; contract print and README carry the logo (`sidra_realestate/branding.py`, `public/images/`). Interim mark in the brand colour until the official artwork file is added
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
