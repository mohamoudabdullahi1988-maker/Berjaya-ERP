# CLAUDE.md — sidra-erp

You are the **implementation** agent for Sidra Real Estate's ERPNext system. Read `docs/SREMS-SRS_v2.0-DRAFT.md`, `docs/CLAUDE-CODE-HANDOFF_v2.0.md` and `docs/HANDOVER_v1.0.md` before any work.

## Project
- Custom Frappe app `sidra_realestate` on **ERPNext v16 / Frappe v16**, Python 3.14, Node 24, MariaDB 11.8. Pinned patch versions: see `docs/ENVIRONMENT_v0.1.md`.
- Modules: Sidra Property, Sidra Sales, Sidra Installments, Sidra Construction, Sidra Brokerage.
- Working spec: `docs/SREMS-SRS_v2.0-DRAFT.md` (decided 5 Nov 2026). Business requirements and IDs come from `docs/SREMS-SRS_v1.6.md`; traceability in `docs/REQUIREMENTS-TRACEABILITY_v2.0-DRAFT.csv`. Handover v1.0 applies where v2.0 is silent.
- The repository stays `sidra-erp` and the app stays `sidra_realestate` (v2.0 writes `sidra_real_estate`).

## Roles
- ChatGPT: architecture, specs, acceptance criteria, security and code review.
- Claude Code (you): code, DocTypes, UI, tests, pull requests.
- Mohamoud / Sidra management: final approval.

## Hard rules
1. Build only against the working spec. Ambiguity or conflict → open a GitHub issue labelled `spec-question`; never guess on money, dates, penalties, refunds or ownership.
2. Never change contract profile values, posting rules, penalty / refund formulas or approval limits without an approved spec version.
3. P0 prototype boundary (SRS v2.0 sections 3.3, 3.4, 9): post no financial vouchers, execute no refunds, apply no late penalties, transfer no title, and allow no per-contract overrides except as decided in issue #13 (D7: for registered External contracts, Sidra Sales Manager confirmation is the INS-19 approval of the contract's own terms). Profile B's legal hold is lifted only as decision D4 specifies (title deadline 20 days; issue #13, `docs/CONTRACT-CAPTURE_v0.3.md`): through the reviewed seed / patch, never by hand or by any other code path.
4. Never edit ERPNext or Frappe core; use DocTypes, Custom Fields, Property Setters, hooks, fixtures, patches in this app.
5. Branch `feature/<module>-<item>` from `develop`; PR into `develop`; CI must pass. `main` only gets release merges.
6. Every feature PR has unit tests and, for DocTypes, Frappe integration tests. Money logic is tested against acceptance cases AT-01 to AT-13 in the handover.
7. Keep `sidra_realestate/__init__.py` version and `CHANGELOG.md` in step. Docs carry their version in the file name and inside.
8. No real customer data or secrets in the repo. Use synthetic names only.
9. PR description follows the template in `.github/pull_request_template.md`.

## Commands
```bash
ruff check sidra_realestate
python -m unittest discover -s sidra_realestate -p "test_engine_*.py" -t .
bench --site sidra.local run-tests --app sidra_realestate
bench --site sidra.local migrate
bench --site sidra.local export-fixtures --app sidra_realestate
```

## Next task
P0 prototype (SRS v2.0 section 7): 10 DocTypes, reservation, Profile A / B, contract snapshot, installment generator, construction job; bench CI. Then the handoff's subsequent PRs.
