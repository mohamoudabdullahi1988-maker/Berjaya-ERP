# Claude Code — implementation handoff for the Sidra ERPNext project

> **Version:** v2.0, issued with SREMS-SRS v2.0-DRAFT (5 Nov 2026).
>
> **Repository note (5 Nov 2026, Mohamoud):** the work stays in `mohamoudabdullahi1988-maker/sidra-erp`, app `sidra_realestate`, until the transfer to a Sidra organisation. The base inputs below map to: `docs/SREMS-SRS_v1.6.md`, `docs/SREMS-SRS_v2.0-DRAFT.md`, `docs/REQUIREMENTS-TRACEABILITY_v2.0-DRAFT.csv`, `CLAUDE.md`. `ACCEPTANCE-TESTS.md`, `DECISIONS-AND-GATES.md` and the redacted v1.6 reference were not supplied; until they arrive the acceptance cases are AT-01 to AT-13 in `docs/HANDOVER_v1.0.md` section 6.

## One-time project setup

The Sidra-owned GitHub organization/repository is the code authority. Claude Code is the development tool, not the GitHub account owner, hosting server or final approver. Create a private repository named `sidra_real_estate` under Sidra's own GitHub organization, or use an existing Sidra-controlled repository explicitly selected by the product owner. Connect Claude Code to it. No credentials in commits.

**Base inputs:** `docs/SREMS-SRS-v1.6-REDACTED-REFERENCE.md`, `docs/SREMS-SRS-v2.0-ERPNext-DRAFT.md`, `docs/REQUIREMENTS-TRACEABILITY.csv`, `docs/ACCEPTANCE-TESTS.md`, `docs/DECISIONS-AND-GATES.md` and `CLAUDE.md`.

### The task to give Claude Code

> Work as lead developer on the Sidra Frappe/ERPNext v16 repository. Read `CLAUDE.md` and all documents under `docs/` before modifying any code. Your first PR must establish an isolated ERPNext v16 staging bench, validate the app package against the chosen pinned Frappe/ERPNext patch versions, install and migrate the `sidra_real_estate` app, and run integration tests for the 10 DocTypes. Fix framework compatibility issues on a feature branch without changing approved business rules. Record commands, errors and test evidence in the PR. In subsequent PRs, complete the P0 demonstration journeys: Scheme → Unit → Reservation; Profile A → Contract → 14-row Hagbad schedule; Profile B legal hold; Construction Job → Stage/BOQ. **Do not post any financial vouchers, execute refunds, apply late penalties or transfer title.** Do not clear Profile B's legal hold. Keep source requirement IDs in PRs. Run pure tests and actual Frappe integration tests. Never push secrets or real customer details.

## First PR acceptance checklist

- [ ] Pin Frappe and ERPNext v16 patch versions and record them in docs; confirm server prerequisites.
- [ ] Confirm packaging through `bench get-app`, `install-app`, `migrate`, and `bench build` without manual DocType creation.
- [ ] Verify standard DocType metadata sync and role installation. Any required fix must be version-controlled.
- [ ] Verify permitted Sales role can reserve from the unit action; an unrelated user is rejected.
- [ ] Verify concurrent reservation against the same unit: exactly one wins.
- [ ] Verify no lease/property ownership or accounting side effects from contract submission.
- [ ] Verify Profile A and B values; drafts from B may be viewed but cannot submit.
- [ ] Verify a Profile A contract with two plots and $11,000 produces 13×$786 + $782.
- [ ] Verify a cash contract dated 29/30/31 can be submitted without a due-date rollover.
- [ ] Verify profile name / frozen snapshot cannot be changed after saving a draft.
- [ ] Verify cancellation of submitted contracts is refused and unit remains protected.
- [ ] Verify construction BOQ totals and cross-Company project validation.
- [ ] Run `bench --site <staging> run-tests --app sidra_real_estate` (create real bench tests if missing).
- [ ] Link screenshots and bench test logs; note any unresolved business decisions.

## Subsequent PRs

1. `feature/sal-price-history` — effective price history; per-Company permissions and import.
2. `feature/sal-contract-parties` — notarized parties, witnesses, bilingual contract clauses, signed-copy gates.
3. `feature/ins-amendments` — manager-approved, versioned changes to draft terms and rescheduling.
4. `feature/con-boq-versions` — approved BOQ revisions, variations, inspection, milestone certification.
5. `feature/fin-voucher-mapping` — only after finance/GL policy is approved; integrate native ERPNext Sales Invoice and Payment Entry with idempotent links.
6. `feature/ins-collections` — historical receipts / payment allocation, statements, aging and reconciliation.

## PR template to use

**Requirement IDs:** ...  
**Business decision/gate:** ...  
**Data model/permissions changed:** ...  
**ERPNext-native objects integrated:** ...  
**Tests (commands and outcomes):** ...  
**Screenshots / source record sample:** ...  
**Open blockers:** ...  
**Rollback / migration impact:** ...

## Important review boundary

An AI review is supplemental. Production release requires Sidra management UAT, Finance control review and legal/Sharia sign-off where applicable. No AI is authorized to remove disputed contract rules by assumption.
