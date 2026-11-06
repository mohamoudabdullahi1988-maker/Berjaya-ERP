# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

## [Unreleased]

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
