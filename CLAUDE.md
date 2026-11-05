# CLAUDE.md — sidra-erp

You are the **implementation** agent for Sidra Real Estate's ERPNext system. Read `docs/HANDOVER_v1.0.md` before any work.

## Project
- Custom Frappe app `sidra_realestate` on **ERPNext v16 / Frappe v16** (branch `version-16`), Python 3.14, Node 24, MariaDB 11.8.
- Modules: Sidra Property, Sidra Sales, Sidra Installments, Sidra Construction, Sidra Brokerage.
- Business rules: `docs/SREMS-SRS_v1.6.md` (section 11 superseded). ERPNext design: `docs/ERPNEXT-MAPPING_v0.1.md`. An ERPNext-specific SRS v2.0 from ChatGPT will supersede both once approved.

## Roles
- ChatGPT: architecture, specs, acceptance criteria, security and code review.
- Claude Code (you): code, DocTypes, UI, tests, pull requests.
- Mohamoud / Sidra management: final approval.

## Hard rules
1. Build only against an approved spec. Ambiguity or conflict → open a GitHub issue labelled `spec-question`; never guess on money, dates, penalties, refunds or ownership.
2. Never change contract profile values, posting rules, penalty / refund formulas or approval limits without an approved spec version.
3. Never edit ERPNext or Frappe core; use DocTypes, Custom Fields, Property Setters, hooks, fixtures, patches in this app.
4. Branch `feature/<module>-<item>` from `develop`; PR into `develop`; CI must pass. `main` only gets release merges.
5. Every feature PR has unit tests. Money logic is tested against acceptance cases AT-01 to AT-13 in the handover.
6. Keep `sidra_realestate/__init__.py` version and `CHANGELOG.md` in step. Docs carry their version in the file name and inside.
7. No real customer data or secrets in the repo. Use placeholder names.
8. PR description: what was built, spec IDs covered (e.g. INS-14), what was left out and why.

## Commands
```bash
ruff check sidra_realestate
python -m compileall -q sidra_realestate
bench --site sidra.local run-tests --app sidra_realestate
bench --site sidra.local migrate
bench --site sidra.local export-fixtures --app sidra_realestate
```

## Next task
Handover section 7: environment → foundation fixtures → installment engine (pure Python, tests AT-01 to AT-13) → stop for review.
