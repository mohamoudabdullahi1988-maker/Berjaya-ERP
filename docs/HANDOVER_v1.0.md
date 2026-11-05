# Sidra Real Estate ERP — Handover to Claude Code v1.0

| Field | Value |
| --- | --- |
| Document | Handover to Claude Code (implementation) |
| Version | v1.0 |
| Date | 5 Nov 2026 |
| Prepared by | Mohamoud Abdullahi Sheikh |
| Repository | `mohamoudabdullahi1988-maker/sidra-erp` (private) |
| Current release | v0.1.0 — Phase 0 skeleton |

Claude Code takes over implementation of Sidra's ERPNext system from this point. ChatGPT owns architecture, specifications and review; Claude Code owns the code, tests and pull requests; Mohamoud / Sidra management give final approval. Claude Code builds against an approved specification and never changes a financial or contract rule on its own.

## 1. Who does what

| Party | Role | Owns |
| --- | --- | --- |
| ChatGPT | Architecture and QA | Requirements, system design, business rules, acceptance criteria, security review, independent code assessment |
| Claude Code | Implementation | The Frappe app repository, Python development, DocTypes, UI, automated tests, pull requests |
| GitHub | Single source of truth | Versioned specifications, source code, issues, pull requests, test results, releases |
| Mohamoud / Sidra management | Final approval | Sign-off of specifications, financial rules, UAT and releases |

| Activity | ChatGPT | Claude Code |
| --- | --- | --- |
| Review SREMS v1.6 | Lead | Secondary review |
| ERPNext-specific SRS v2.0 | Lead | Validate feasibility |
| Business processes and workflows | Lead | Implement |
| Custom Frappe DocTypes | Lead logical design | Implement schema |
| Financial transaction specifications | Lead, with Finance sign-off | Implement approved logic |
| Contract profiles A / B | Define rules and acceptance tests | Develop and test |
| Property inventory and reservations | Define workflow and constraints | Develop |
| Construction project management | Define workflows, costing, controls | Develop |
| Customer portal and dashboards | Functional design | UI and backend |
| GitHub repository operations | Review specifications and PRs | Primary code contributor |
| Automated unit / integration tests | Define acceptance cases | Write and run tests |
| Security and code review | Lead review | Fix findings |
| Deployment | Review readiness | Execute in an authorised environment |
| UAT and release authorisation | Assess against SRS | Resolve defects |

## 2. Rules Claude Code must follow

1. **Specification first.** Build only what an approved document in `docs/` describes. If the spec is silent, ambiguous or contradicts itself, open a GitHub issue labelled `spec-question`, state the options, and continue with other work. Do not guess on money, dates, penalties or ownership.
2. **No silent rule changes.** Contract profile values, posting rules, penalty and refund formulas, and approval limits change only through an updated, approved spec version.
3. **Never edit ERPNext or Frappe core.** Everything lives in `sidra_realestate`: DocTypes, Custom Fields, Property Setters, hooks, fixtures, patches.
4. **Branches and PRs.** Work on `feature/<module>-<item>` from `develop`; open a PR into `develop`; CI must pass. `main` receives only release merges from `develop`.
5. **Tests with every feature.** Each PR includes unit tests for its business logic. Pricing, schedules, allocation, penalties, refunds and postings must have tests built from the acceptance cases in section 6.
6. **Versioning.** App version in `sidra_realestate/__init__.py` and `CHANGELOG.md` move together. Documents in `docs/` carry their version in the file name (`NAME_vX.Y.md`) and inside; a revision is a new file version plus a changelog line.
7. **No real personal data.** Customer names in code, fixtures, tests and docs are placeholders (for example Ayaan Cali Warsame, Cabdiraxmaan Yuusuf Jaamac). Never commit real customer names, ID numbers, phone numbers or signed contracts.
8. **No secrets in Git.** Site config, passwords, API keys and WhatsApp tokens stay on the server.
9. **Report, don't hide.** Every PR description lists what was built, which spec items it covers (IDs such as INS-14), what was not done and why.

## 3. Documents (read in this order)

| File | Status | Use |
| --- | --- | --- |
| `docs/HANDOVER_v1.0.md` | Current | This file: roles, rules, plan, first tasks |
| `docs/SREMS-SRS_v1.6.md` | Approved business requirements | All business rules; section 11 (Laravel) is superseded |
| `docs/ERPNEXT-MAPPING_v0.1.md` | Draft | Which ERPNext feature covers each requirement; custom DocType list |
| `docs/SRS_v2.0` (ERPNext-specific) | Coming from ChatGPT | When committed and approved, it supersedes v1.6 and the mapping |

## 4. Fixed decisions

These are settled. Do not change them without an approved spec update.

| Topic | Decision |
| --- | --- |
| Platform | ERPNext v16 + Frappe v16 (branch `version-16`), Python 3.14, Node 24, MariaDB 11.8 |
| App | `sidra_realestate`, modules: Sidra Property, Sidra Sales, Sidra Installments, Sidra Construction, Sidra Brokerage |
| Repository | Stay on `mohamoudabdullahi1988-maker/sidra-erp` for now; transfer to a Sidra-owned organisation later |
| Size | 1 office, under 10 staff users |
| Payment channels | Cash at office, bank transfer, ZAAD, eDahab — one Mode of Payment and account each |
| Customer messaging | WhatsApp Business API (connector choice in the portal / messaging phase) |
| Late penalties | Sidra income (charity account stays available as a profile setting) |
| Early settlement | Discount only at General Manager's discretion |
| Installment markup | Varies by deal: per-contract setting, 0% allowed; cash price always stored |
| Construction billing and retention | Per contract |
| Design and inspection fees | Quoted per job |
| Brokerage commission | Per deal |
| Off-plan house payments | Per buyer: stage-based or monthly |
| Live data to migrate | 50–200 installment contracts in Excel |
| Branding | Logo from sidrahomes.co |

### 4.1 Contract profiles (SRS v1.6 section 5.5)

Every contract copies its profile into a frozen terms snapshot; a per-contract change needs Sales Manager approval and is audited. Changing a profile never changes signed contracts.

| Setting | Profile A (default) | Profile B |
| --- | --- | --- |
| Down payment | None | Fixed amount at signing (e.g. $3,000) |
| Installments | 14 | 24 |
| Grace before first installment | 0 months | 3 months |
| Due day | 5th | 10th |
| Markup | 0% | 0% |
| Buyer late penalty | $5 a day, capped at $150 a month | $100 fixed after a 15-day written notice |
| Default trigger | 2 consecutive missed installments | Off |
| Refund on default | Paid amount less one installment | Not set |
| Title deadline after final payment | 20 days | 20 days (contract text also says 14 — see open items) |
| Sidra title delay penalty | $5 a day | $220 a month |
| Buyer refund right if title late | Off | After 90 days, refund + 10% |
| Early payment | Allowed, reduces the last installments | Same |

Hagbad Round 2 full plot ($11,000) uses Profile A. The Hagbad half plot ($5,500) is $250 a month for 22 months.

## 5. Delivery plan

Phase order agreed on 5 Nov 2026 (ChatGPT's order). It replaces section 12 of SRS v1.6.

| Phase | ChatGPT delivers | Claude Code delivers | Release |
| --- | --- | --- | --- |
| 0. Foundation | Revised SRS v2.0, architecture, DocType catalogue, acceptance criteria | App scaffold (done in v0.1.0), repo structure, development environment, roles, accounts, Modes of Payment | v0.1.x |
| 1. Property | Unit registry, reservation rules, pricing history | Scheme, Property Unit, Reservation, price history, availability view | v0.2.0 |
| 2. Sales | Contract profiles A / B, approvals, clause specifications | Contract Profile, Sale Contract, parties, clauses, terms snapshot, Somali / English print format | v0.3.0 |
| 3. Collections | Installment algorithms, allocation and reconciliation test cases | Schedules, invoices, receipts, penalties, customer statements | v0.4.0 |
| 4. Construction | Project stages, BOQ, variations, project-cost rules | Construction module on Project / Task | v0.5.0 |
| 5. Finance | Posting matrix, controls, UAT and reconciliation tests | Approved ERPNext financial integrations | v0.6.0 |
| 6. Release | Gap assessment and readiness review | Bug fixes, automated tests, deployment | v1.0.0 |

**Prototype target:** Phases 0–2 plus a working installment schedule generator from Phase 3. Full integrated deployment is not the near-term goal.

## 6. Acceptance cases to build tests from

ChatGPT confirms or replaces these in its acceptance criteria. Until then they are the working test set.

| ID | Case | Expected result |
| --- | --- | --- |
| AT-01 | Profile A, $14,000, 0 down, 14 months, signed 2025-08-31 | 14 installments of $1,000, due on the 5th, first 2025-09-05, last 2026-10-05 |
| AT-02 | Profile A, Hagbad full plot $11,000, 14 months | 13 × $786 then 1 × $782 (rounding absorbed by the last installment); total $11,000 |
| AT-03 | Profile B, $9,000, $3,000 down, 24 months, 3-month grace, signed 2026-01-15 | 24 × $250 due on the 10th, first 2026-04-10, last 2028-03-10 |
| AT-04 | Hagbad half plot $5,500, 22 months, 0 down | 22 × $250 |
| AT-05 | Murabaha formula: P $30,000, D $9,000, r 10% a year, n 24 | Profit $4,200; sale price $34,200; installment $1,050 ($875 cost + $175 profit) |
| AT-06 | Profile A, installment 3 days late | Penalty $15 |
| AT-07 | Profile A, installment 40 days late in one month | Penalty capped at $150 for that month |
| AT-08 | Profile A, 2 consecutive installments missed, $5,000 paid so far, installment $1,000 | Contract flagged for cancellation review; refund $4,000 |
| AT-09 | Profile B, installment late, notice served, 15 days pass unpaid | One $100 penalty |
| AT-10 | Payment $1,500 against two overdue $1,000 installments | Oldest fully paid, next $500 paid, $500 outstanding |
| AT-11 | Profile A, final payment received, title not issued after 23 days | Sidra delay penalty $15 |
| AT-12 | Profile edited after a contract is signed | Signed contract terms unchanged |
| AT-13 | Early extra payment $2,000 on AT-01 after 6 installments | Last two installments cleared; schedule ends 2 months early |

## 7. First tasks for Claude Code

In this order, each as its own branch and PR into `develop`:

1. **Environment** — set up a local or staging bench (Frappe / ERPNext `version-16`, site `sidra.local`), install `sidra_realestate`, turn on developer mode. Add a full bench test job to CI (install ERPNext + app, `bench run-tests --app sidra_realestate`).
2. **Foundation fixtures** — Sidra roles (section 3 of the mapping), extra chart-of-accounts entries (mapping 2.5), Modes of Payment: Cash, Bank Transfer, ZAAD, eDahab. Export as fixtures.
3. **Installment engine (pure Python, no DocTypes)** — `sidra_realestate/sidra_installments/engine/`: pricing (5.1), schedule generation (grace, due day, rounding on last installment, zero down), payment allocation (oldest first), penalty calculation (per-day with cap, fixed after notice), default check and refund, early payment. Tests AT-01 to AT-13. This is the demonstrable Phase 3 generator and has no ERPNext dependency.
4. **Phase 1 DocTypes** — Sidra Scheme, Sidra Property Unit (fields in SRS 4.4 SAL-12 / SAL-14), Sidra Reservation with daily expiry job.
5. **Phase 2 DocTypes** — Sidra Contract Profile (all 5.5 settings, Profile A / B as fixtures), Sidra Contract Clause, Sidra Sale Contract (units and parties child tables, terms snapshot, override approval workflow), contract print format in Somali and English.

Stop for review after task 3: the engine's results go to ChatGPT and Mohamoud before DocTypes depend on it.

## 8. Environment and access

| Item | Status |
| --- | --- |
| GitHub repo | Created, `main` and `develop` pushed (commit `0ba5524`) |
| Tag `v0.1.0` | Not yet on GitHub — the earlier session could not push tags; Mohamoud creates tags and releases from the GitHub web page |
| Staging server | Not available yet — needed before Phase 1 sign-off (cloud VPS, Ubuntu 24.04) |
| Branch protection on `main` | To set up: require PR and passing CI |
| ChatGPT GitHub access | To be connected by Mohamoud for PR review |

## 9. Open items

| Item | Owner |
| --- | --- |
| ERPNext-specific SRS v2.0 | ChatGPT |
| Confirm acceptance cases AT-01 to AT-13 | ChatGPT, Mohamoud |
| Web address for staff and customer portal | Sidra |
| Whether ERPNext is the main accounting ledger | Sidra Finance |
| Contract B wording: title deadline 20 days (clause 4) vs 14 days (clause 6); payment dates in the text do not match 24 months | Sidra |
| WhatsApp connector choice (community app or custom) | ChatGPT design, Claude Code test |
| Repository transfer to a Sidra organisation | Mohamoud, later |
| Staging server | Mohamoud |
