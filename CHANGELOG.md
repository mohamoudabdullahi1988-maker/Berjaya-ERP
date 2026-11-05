# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

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
