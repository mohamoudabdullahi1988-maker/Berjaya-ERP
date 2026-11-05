# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

## [Unreleased]

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

### Changed
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
