# Changelog

All notable changes to `sidra_realestate`. Versions follow `MAJOR.MINOR.PATCH`; each release is tagged in Git.

## [Unreleased]

### Changed (v0.1.18 — Berjaya product name on the existing screens, 13 Nov 2026; decisions G17–G20)
- **Decisions recorded** in `docs/DECISIONS-AND-GATES_v0.1.md`: G17 (interface rebuild), G18 (product name **Berjaya**), G19 (**Sidra** stays the client and company name), G20 (rollout: `/berjaya`, charcoal and terracotta, rebrand first). `CLAUDE.md` and `AGENTS.md` carry the same naming rule.
- **Branding audit** (`docs/BERJAYA-BRANDING-AUDIT_v0.1.md`): 2,128 "sidra" lines classified — 11 product, 176 client, 1,883 internal, 58 unsure. Approved by Mohamoud on 13 Nov 2026.
- **Rules audit** (`docs/BERJAYA-RULES-AUDIT_v0.1.md`): every rule held in Desk form scripts or field conditions, with its server check. Document only; no rule moved.
- **Surfaces rebranded**: the app name on the apps screen, the system and website name (browser tab titles, login page, website footer), the `/sidra` front page title and header, the `/sidra-staff/` page title and sidebar brand, the README title and the app description. The name comes from one constant, `sidra_realestate.branding.BRAND_NAME`.
- A plain text wordmark and letter icon (`berjaya-wordmark.png`, `berjaya-icon.png`, `berjaya-favicon.png`) replace the company logo as the software's navbar logo, splash and favicon. Colours are unchanged.
- A site this app had branded "Sidra Homes" is rebranded on migrate: only that exact earlier value in System, Website and Navbar Settings is replaced. An administrator's own value is still left alone.
- **Unchanged**: Company **Sidra Homes** and every record in it; the Sidra Homes logo and letterhead on the contract and quotation prints; app, module, site, flag, DocType, role and report names; naming series; the routes `/sidra` and `/sidra-staff/`; the Desk sidebar names; the native Android and macOS apps; every guard, loader, posting gate and permission. No patch, no data migration.
- Tests: product-name source, hooks and apps-screen tile; login page and front page render Berjaya; earlier branding replaced; Company list and name unchanged by branding; contract print and a Sidra Homes sales invoice print carry no product name.

### Fixed (v0.1.17 — staff dashboard pilot sources and installment calendar, 13 Nov 2026)
- Read opted-in native financial data from either the twelve-month pilot manifest, the earlier finance demo manifest, or both. Preserve complete permission-filtered invoice/payment cohorts, currency checks and ownership validation; no grants, postings or loader calls.
- Remove the two historical demo Companies from the staff dashboard selector and prefer Sidra Homes, without changing any Company or historical record.
- Add a complete, permission-filtered monthly installment endpoint and responsive Calendar/List views with month navigation, day selection, search, date filters and exact server schedule cards. Scheduled obligations and past dates remain explicitly unreconciled; posted receipts and overdue invoice balances use their separate native sources.
- Show open construction jobs including enquiries and a status breakdown; replace the unconnected project-baseline headline with recorded overdue milestones, preserving the unavailable baseline API field. Label the existing stage-percentage average explicitly.


### Added (v0.1.15 — twelve-month pilot demonstration dataset, 13 Nov 2026; decision G16; `docs/PILOT-DEMO_v0.1.md`)
- **`sidra_realestate.pilot_demo.create_pilot_demo_data`**: one guarded, manual loader that fills the existing Company **Sidra Homes** with twelve months of fictional movement, so a client demonstration opens onto populated records in every module instead of empty screens.
  - Property: 4 schemes, 120 units across Plot / House / Apartment, ready and off-plan, with 20 submitted price reviews scheduled ahead.
  - Sales: 40 buyers with KYC (4 left unverified so the contract gate is visible), 60 quotations across Draft / Issued / Expired with discounts above and below the 5 % limit, 25 reservations created through the Reserve Unit service, 45 contracts — Cash and Installment, generated and externally registered, 3 left draft — and 20 title transfers spread across their states.
  - Installments: a schedule on every installment contract at 12, 18, 24 or 36 months; the rounding lands on the final row so the schedule equals the balance exactly.
  - Construction: 25 jobs across all four service types and six statuses, each with a BOQ, five stages and billing percentages totalling 100; a draft quotation per job past Enquiry and addition-only variation orders.
  - Finance: about 160 vouchers over twelve months — opening capital, 60 sales invoices, 35 purchase invoices and their payments — paid, part paid and open in equal thirds so AR ageing has more than one bucket.
- **Every G14 guard is kept and none relaxed**: Administrator only, all three staging flags, a private ownership manifest (`sidra-pilot-demo-v1.json`), the no-foreign-GL guard as the first read before any insert, one transaction with full rollback, reserved-identity refusals, and a rerun that verifies and writes nothing.
- The pilot and finance demo manifests are read together, so the two datasets coexist in Sidra Homes and each still refuses ledger rows neither owns.
- `services/pilot_dataset.py`: the dataset plan as pure, seeded logic with `test_engine_pilot_dataset.py` — counts, dates, schedule arithmetic and the balance-sheet identity are asserted before anything is posted. Frappe integration tests cover the guards, the rollback, the foreign-GL refusal, module coverage and the rerun.
- `docs/PILOT-DEMO_v0.1.md`, `docs/DECISIONS-AND-GATES_v0.1.md`: G16. `CLAUDE.md` and `AGENTS.md` name the pilot dataset in the scoped exception.
- Known gap: **Sidra Brokerage has no DocTypes**, so it is not populated and its sidebar section stays empty. Inspection Reports are not created — the DocType needs an inspector User the loader does not make.
- Production posting gates, refunds, penalties and title transfer are unchanged; ERPNext remains the only ledger.

### Added (v0.1.14 — one front page for staff, decision G15, 13 Nov 2026; `docs/SHELL_v0.1.md`)
- `/sidra`: a single front page with four doors (Executive Dashboard, Financials, Real Estate Sales, Construction). Each service shows its workflow as numbered steps with counts, items waiting for action, and New buttons. Doors, steps and buttons follow the user's permissions; a step the user can't read is left out, not shown as zero.
- Staff land on it after signing in: the app's apps-screen route is `/sidra` (desk route `/desk/sidra-sale-contract`) and System Settings Default App is set to this app when blank.
- Read-only and server-rendered: no new HTTP API, no posting, not cached. The staff dashboard is unchanged and linked from the page.
- `api/test_shell.py`: Frappe integration tests. `docs/DECISIONS-AND-GATES_v0.1.md`: G15.

### Changed (v0.1.13 — sample data under Sidra Homes on the test site, decision G14, 13 Nov 2026)
- Decision G14 recorded in `docs/DECISIONS-AND-GATES_v0.1.md`; `docs/FINANCE-DEMO_v0.2.md` replaces v0.1 (kept, marked superseded); `CLAUDE.md`, `AGENTS.md`, `docs/DEPLOYMENT_v0.1.md` and `docs/STAFF-DEMO_v0.1.md` name Sidra Homes.
- Finance demo loader posts the same ten vouchers (237,000 / 237,000) into the existing Company **Sidra Homes**, named in one constant. It never creates or edits the Company; demo accounts sit under marked `Fictional Demo Accounts` groups; identities are `SHD`, so the v0.1 `SFD` records and both old demo Companies are untouched.
- New no-foreign-GL guard: before the first insert, refuse a Company holding any GL entry the private manifest does not own, naming the count and first vouchers; refuse on a missing, duplicated or unreadable manifest. Also run by `verify_finance_demo`.
- Staff dashboard demo finance adapter and `demo_reporting.populate_and_verify` follow the same constant to Sidra Homes.
- Tests: finance demo tests retargeted; new tests for the guard (refusal, count in the message, nothing written), the missing Company, the unreadable manifest, and the count and checksum of 60 existing units before and after a load.
- `deploy/sidra-homes-verify_v0.2.sh`: test-site runbook and read-only verification sweep. `deploy/sidra-homes-run_v0.1.sh`: one script that backs up, fast-forwards the app to `develop`, rebuilds, restarts and then runs it.

### Added (v0.1.12 — sale quotation, P1, 12 Nov 2026; decision G13; `docs/SALE-QUOTATION_v0.1.md`)
- **Sidra Sale Quotation** (SAL-05): an offer for one or more units showing the cash option and the installment option side by side, printed on Sidra letterhead (print format *Sidra Sale Quotation*).
  - Cash option: the unit's listed price, or lower as a discount.
  - Installment option: a price entered per unit, never below the listed price; terms from a contract profile, with the number of months adjustable from 12 to 36; an indicative schedule.
  - Discounts need a second person before the quotation is issued: a Sales Manager up to 5 % of the unit's listed price, the General Manager above. Changing a price clears the approval.
  - Valid 7 days unless changed; a daily job marks issued quotations Expired.
  - Offer only: no reservation, no unit change, no contract and no posting.
- Real Estate sidebar link for Sale Quotations.
- `services/quotation.py`: pure rules with `test_engine_quotation.py`. The 5 % limit, the month range and the valid days are constants that change only with an approved spec. Frappe integration tests.
- `docs/DECISIONS-AND-GATES_v0.1.md`: G13.

### Fixed (v0.1.11 — staff sample figures, 12 Nov 2026)
- Staff Sales shows permission-filtered recorded lead statuses for the selected Company and period. Qualification/conversion remain unset.
- Add a single staging finance-demo population script with ledger and staff-source checks and correctly scoped report links.

### Added (v0.1.10 — buyer KYC and title transfer tracker, P1, 12 Nov 2026; decision G12; `docs/KYC-AND-TITLE_v0.1.md`)
- **Sidra Customer KYC** (SAL-07): one restricted record per Customer with ID or passport, phone, address, guarantor details and private scans. Sales Users enter it and a Sales Manager verifies it; the General Manager reads. No other role has access. Changing a verified record returns it to Draft.
- **Contract gate:** a contract generated from a profile can't be submitted until the buyer has verified KYC. Registered (external) contracts don't need it.
- **Sidra Title Transfer** (SAL-08, SAL-18):
  - one record per unit of a confirmed contract, with documents required, land office submission, deed number and handover;
  - the final payment date is entered with private evidence and confirmed by a second Sales Manager; the deadline is the contract's frozen title deadline days after it;
  - status is Due Soon from 5 days before the deadline and Overdue after it, with days past the deadline; a daily job keeps it current;
  - the General Manager confirms the handover, after which the record is locked;
  - record only: no change to the unit, the contract or ownership, and no late-title amount.
- Real Estate sidebar links for Title Transfers and Customer KYC; Title connection on the sale contract.
- `services/title.py`: pure deadline rules with `test_engine_title.py`. `services/files.py`: the shared private-file check. Frappe integration tests for both DocTypes and the contract gate.
- The demo loader gives its fictional buyers verified KYC so generated demo contracts can still be confirmed.
- `docs/DECISIONS-AND-GATES_v0.1.md`: G12.

### Added (v0.1.9 — construction controls, P1, 12 Nov 2026; decision G11; `docs/CONSTRUCTION-CONTROLS_v0.2.md`)
- **Sidra Construction Quotation** (CON-02, CON-03):
  - priced from a frozen copy of the job's BOQ, or as a fixed fee; printed on Sidra letterhead (print format *Sidra Construction Quotation*);
  - the Project Manager issues it; it can't be issued if the BOQ has changed since the draft or the quotation has expired; issuing moves the job to Quoted;
  - the client's acceptance is recorded with a private signed file;
  - **Approve Contract** is for the General Manager only. It sets the job's original contract value, start, duration, end and retention (0–10 %, period in months), and the job becomes Contracted. Stage Billing % must add up to exactly 100.
- **Sidra BOQ Revision** (CON-02 revisions): the Project Manager approves; revisions are numbered and copy their lines to the job. Stale drafts and revisions that change nothing are refused. Never cancelled. The job's BOQ changes only through a new revision.
- **Sidra Variation Order** (CON-06):
  - additions only, with the client's approval recorded (who, when, private signed file);
  - a second person approves: another Project Manager up to $1,000, the General Manager above $1,000, and cancelling follows the same rule;
  - the job must have an approved contract.
- **Sidra Inspection Report** (CON-05): date, inspector, stage, checklist results, overall result, defects, next action and due date, private photos. Consistency checks apply. The Inspector approves.
- **Stage certification** (CON-04): **Certify Stage** for the Project Manager on Completed, 100 %, ended stages. A certified stage is frozen and can't be removed. Not an invoice or revenue.
- **Sidra Construction Job:**
  - contract section, read-only and set only by Approve Contract;
  - Approved Variations and Current Contract Value;
  - Milestone Amount per stage (current value × Billing %; adds up to the value exactly);
  - Billing % locked after the contract;
  - Approved BOQ Revision;
  - Create buttons, Connections and Construction sidebar links.
- `services/construction.py`: pure rules with `test_engine_construction.py`. The $1,000 limit and 10 % retention ceiling are constants that change only with an approved spec. Frappe integration tests for each new DocType, contract approval and certification.
- `docs/DECISIONS-AND-GATES_v0.1.md`: G11.
- Recorded only: no invoice, Sales Order amendment or posting (`CLAUDE.md` rule 3).

### Security (v0.1.8 — ERPNext hardening, 12 Nov 2026)

- Bind contract-import spreadsheets to their own private File attachment and enforce File read permission before parsing.
- Enforce Customer access on reservations and linked-unit access on cancellation; reject malformed durations and nonfinite spreadsheet amounts before writes.
- Add regression tests, a read-only administrative site-security audit, and repeatable secret/Bandit CI checks. See `docs/SECURITY-REVIEW_v0.1.md` for findings and outstanding deployment verification; no AI runtime is bundled or added.

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

