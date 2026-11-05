# Sidra Real Estate Management System — ERPNext Implementation Specification

> **Repository note (5 Nov 2026, Mohamoud):** v2.0-DRAFT is the working specification for implementation. The repository stays `sidra-erp` and the app keeps the name `sidra_realestate`; read `sidra_real_estate` below as `sidra_realestate` (so `sidra_real_estate.services…` is `sidra_realestate.services…`). Handover v1.0 stays in force where this draft is silent. Questions on this draft are GitHub issues labelled `spec-question`.

**Document ID:** SREMS-SRS  
**Version:** v2.0-DRAFT (ERPNext redesign; not an approved functional baseline)  
**Date:** 5 November 2026  
**Source baseline:** SREMS-SRS v1.6, 5 November 2026, prepared for Sidra Real Estate management.  
**Target:** Frappe Framework 16 + ERPNext 16 + the proprietary `sidra_real_estate` Frappe app.  
**Scope:** Sidra-owned land and houses (including off-plan), installment sales / contracts, construction/design/inspection services, land brokerage, customer management, and financial integration.  
**Prototyping caution:** This document covers the **target solution**. Only the explicitly marked `P0 prototype` subset is implemented in the accompanying source. Unapproved legal/Finance rules are blocked by design.

## 1. Decision record and source preservation

1. Retain the five **business requirement areas** from v1.6: Construction Projects, Property Inventory & Sales, Murabaha/Installments & Collections, Finance & Accounting, and CRM/Portal/Notifications. Land brokerage remains in scope under property services.
2. Replace Laravel/Filament/standalone MySQL tables with standard Frappe DocTypes and ERPNext-native documents. Avoid a second `customers`, `invoices`, `payments`, or general-ledger subsystem.
3. Preserve source requirement identifiers `CON-*`, `SAL-*`, `INS-*`, `FIN-*`, `CRM-*` in backlog, stories, code comments and tests. See `REQUIREMENTS-TRACEABILITY.csv`.
4. Preserve Profile A and Profile B **as described** in v1.6, allowing a non-submitted draft but with a submission legal hold on Profile B until its conflicting 14/20-day title deadline is resolved. Do not silently select one deadline.
5. Keep the v1.6 decision that contract terms vary by deal. Any profile override must undergo separate approval; **prototype prohibits overrides** and snapshots profile terms at contract creation.
6. Record v1.6's choice of Sidra income for buyer-late penalties as a *source decision*, not as authorization to post them. Sharia/legal review is required; prototype only stores a `Pending Policy Sign-off` destination.
7. Retain the business scope of **construction, design, inspection, land sales, house sales, and brokerage**. Leasing was discussed earlier as a possible generic capability, but is **not present in the supplied v1.6 scope** and is excluded unless management authorizes a change.
8. Source v1.6 says one office and fewer than 10 users, with 50–200 live installment contracts in Excel. Build for that initial scale; consider multi-company/multi-branch only when validated.

## 2. Implementation boundaries

### 2.1 System of record

| Record type | Authoritative object | Custom extension / linkage |
|---|---|---|
| Legal company | ERPNext `Company` | Link on Sidra Scheme / Contract / Job |
| Customer / buyer / tenant-like party | ERPNext `Customer`, `Contact`, `Address` | Restricted Sidra KYC data (phase P2) |
| Lead / sales opportunity | ERPNext `Lead`, `Opportunity` | Property/plot interest fields (phase P2) |
| Quotation | ERPNext `Quotation` | BOQ and job service-type logic |
| Construction engagement | ERPNext `Project`, `Task`, `Sales Order` where appropriate | `Sidra Construction Job`, stage template, inspection and variations |
| Plot / house unit | Custom `Sidra Unit` under `Sidra Scheme` | Not fungible stock; unique identified property |
| Reservation | Custom `Sidra Reservation` | No GL posting from reservation itself |
| Property sales agreement | Custom `Sidra Sale Contract` | Unit links, frozen terms, signed contract and title obligations |
| Contractual installments | Child `Sidra Installment Line` | Do **not** confuse with ERPNext Accounts Receivable |
| Sales billing / receivables | ERPNext `Sales Invoice` | Mapping to contract and scheduled obligation **after Finance sign-off** |
| Receipt/settlement | ERPNext `Payment Entry` | Mapping to the agreement and due installment; no duplicate custom cash ledger |
| General ledger | ERPNext GL and Payment Ledger | Native vouchers only; approved account mappings |
| Supplier payment / expense | ERPNext `Purchase Invoice`, `Payment Entry`, `Journal Entry` | Cost codes and construction project dimensions |
| Documents | Frappe `File`, private attachments and Print Formats | Contract templates in Somali and English |
| Notifications | Frappe email/SMS integration + approved WhatsApp provider | Outbound message log and opt-out rules |

### 2.2 Deployment topology

- One private GitHub repository containing the versioned Frappe app and specifications.
- ERPNext/Frappe v16 on a **staging VPS** with MariaDB, Redis, workers, scheduler, HTTPS and daily encrypted backups. Use managed infrastructure if available.
- Site locale: English UI first, Somali contract/receipt templates, base currency USD; convert SLSH with approved exchange-rate source and ERPNext currency precision. Local timezone `Africa/Mogadishu`.
- Separate staging and production sites, independent credentials and backup sets. Test restores; no direct testing against live customer data.
- Off-server backups, monitoring, restricted DB access, secret management, pinned container/app versions and audited deployment.

### 2.3 Primary transaction design rules

- **Property/unit status:** physical/legal availability state is separate from accounting state, price state and title state. Reservation and contract allocation operations serialize on the `Sidra Unit` row.
- **Contract invariants:** unique unit IDs per contract; sum of allocated unit prices equals the agreed contract price; immutable signed-profile snapshot; no silent changes after contract submission.
- **Scheduling:** a contract due schedule is a commercial obligation, *not* recognition of revenue, a receipt, or a posted receivable by itself.
- **Posting:** use ERPNext vouchers with a unique source reference, idempotent posting, reciprocal links, and payment reconciliation. **No duplicate custom financial ledgers.**
- **Separation of duties:** sales may draft, sales management approves discounts/overrides, Finance validates postings, GM authorizes write-offs/title exceptions; system administrators should not automatically be business approvers.
- **Cancellation:** no automatic property release until legal status, financial reversal, refund liability and approvals are reconciled.

## 3. Functional modules and workflow design

### 3.1 Construction Services (CON-01..CON-15)

**Supported types:** Full Construction, Design Only, Inspection Only, and Beacon/Foundation (from Contract A's land buyer condition).

**ERPNext foundation:** Customer → Opportunity → Quotation → Sales Order (if used) → ERPNext Project/Tasks → milestone invoice via Sales Invoice → ERPNext AR and Payment Entry.

**Sidra extension:** Construction Job, Stage Template and Stage, BOQ with revisions, Inspection Report, Variation Order, Work Package, Retention Schedule and Defects/Snag records. The prototype implements Construction Job, Stage and BOQ **entry** only. Further features below are target scope, not currently executable.

**Operational workflow:** Enquiry → Site/Service Details → Scope/BOQ Quotation → Contract → Project Baseline → Site Progress/Inspections → Approved Variation(s) → Certified Milestone → Invoice → Receipt → Handover → Defects → Final Closeout.

**Core data:** Company, Customer, site location/GPS/title reference, service type, quotation, project, contract value, start/end, milestone %, assigned engineer, inspection checklist/photos, BOQ revision, approved change order, invoices, retention percentage, funding and final account.

**Commercial constraints:** schedule values and latest approved variations must reconcile to contract total; progress sign-off ≠ revenue recognition; actual costs and open commitments must be reported separately; project costs must be captured if claiming project-margin accuracy. The 3 independent quotations requirement for beacon/foundation procurement must be demonstrable before award. Retention is not released without defects/approval workflow.

### 3.2 Property Inventory and Sales (SAL-01..SAL-20)

**Master hierarchy:** Scheme → Block/Phase → Unit. Unit supports plot/house/apartment, full/half plot, measured area/dimensions, district/neighbourhood/original land parcel, east/west/north/south boundaries, title reference, off-plan delivery, photographs/map location and effective-date price history.

**Status model (target):** `Available`, `Reserved`, `Under Contract`, `Sold`, `Blocked`; separate `title_status` (`Not Ready`, `Pending Filing`, `Transferred`) and `construction_status` (`Planned`, `In Progress`, `Ready`). Prototype only persists primary unit availability with status progression to `Under Contract`.

**Reservation workflow:** Select available unit → identify Customer → validate existing reservations and state under row lock → create time-limited reservation → confirm / expire / cancel. Reservation deposit **requires a native ERPNext Payment Entry or advance workflow**, not an informational field alone, before production. On expiry the unit returns to available only if no newer active allocation exists.

**Sales workflow:** Select one or multiple units → create quotation (cash/deferred offer) → KYC/agent/notary parties → choose contract profile → approve overrides → freeze terms and clauses → issue Somali/English notary-ready contract → attach signed copy → billing/collection → title deadline monitoring → authorized transfer and evidence.

**Target legal-party details:** seller, guarantor/pledged property, two witnesses, buyer agent (wakiil), notary name and ref, document attachments. Profile-specific restrictions must be selected and printed. Prototype includes buyer agent, notary reference, attachment but not a complete legal-party/clause engine.

**Brokerage:** third-party property owner/listing/commission must be separate from Sidra-owned inventory and from property sale revenue; record brokerage mandate, verification report, closed-sale evidence and commission invoice. Planned P2.

### 3.3 Contract profiles and collections (INS-01..INS-21)

**Contract fields:** profile, type, Customer, Company, agreed signed selling price, optional cash offer price, purchase/development carrying cost (later), actual down payment obligation, remaining contractual balance, units with price allocation, signed date and schedule. **Do not use cash offer price as property asset cost.**

**Term snapshot:** save a copy of Profile A/B terms on each new contract; signed contracts must retain their historical terms even after a profile changes. Overrides require approval and must be versioned, not edited in place. Prototype does not permit overrides.

**Profile A:** default 14 installments, down payment 0, grace 0, day 5, zero additional markup in specimen, $5/day buyer penalty capped at $150/month, 2 missed months trigger cancellation **review** (not automatic cancellation), title due 20 days after final *verified* payment, $5/day late-title term. Term storage is implemented; legal/financial enforcement is not.

**Profile B:** 24 installments, fixed $3,000 down, 3 months' grace, day 10, fixed $100 after written notice of 15 days, $220/month late-title term and possible refund+10% after 90 days. **Legal hold** until original contract clauses reconcile 14-day vs 20-day title deadline. Production contract signing under this profile is prohibited until resolved.

**Hagbad examples:** full plot $11,000 / 14 months / no down -> 13 × $786 + $782 final. Half plot $5,500 / 22 months -> 22 × $250. Existing price agreement prevails over generic financing example.

**Installment algorithm:** `balance = agreed_sale_price - contractual_down_payment`; first due date is the first specified day of month **on or after** contract date, plus configured grace months; subsequent dues monthly. Round all but last installment to whole USD under Profile A/B, final absorbs remainder; *this first-due-date interpretation is a proposed implementation clarification requiring Sidra sign-off*.

**Collections target:** actual receipt in ERPNext Payment Entry with cash/bank/ZAAD/eDahab account; allocate oldest unpaid installment first and preserve a separate audit record of which due lines were satisfied. Advance/partial receipts, overpayments, reconciliation, cancellations, defaults and early settlement/ibra' require explicit workflows, not silent balance edits. Printed receipts must reference *posted* vouchers.

**Revenue and Sharia rule:** source v1.6 mixes "Murabaha profit" and "cost recovery" with selling price and uses collection-timed recognition. Finance/Sharia professionals must approve accounting treatment for completed properties, off-plan construction, deferred price components, and penalties. **Prototype does not post anything to the ledger.**

### 3.4 Finance (FIN-01..FIN-10)

ERPNext handles Account, Company, Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry, Payment Terms, GL/Payment Ledger, fiscal period close, bank reconciliation and financial statements. Build only mappings and reporting not served natively.

**Financial event matrix (approval gate):**

| Event | Proposed ERPNext handling | Gate |
|---|---|---|
| Reservation (no receipt) | Commercial record only | Prototype |
| Reservation deposit actually received | Native advance/payment voucher; liability treatment per approved policy | Finance approval |
| Signed sale contract | Commercial agreement and schedule; no assumed cash | Prototype |
| Invoice/receivable | ERPNext Sales Invoice only when recognition and billing policy establishes trigger | Finance approval |
| Cash/bank/mobile-wallet receipt | ERPNext Payment Entry; external reference deduplicated | Finance approval + integration QA |
| Revenue and property cost-of-sales | Standard voucher flow after asset classification and transfer basis agreed | Finance approval |
| Penalty due and collected | No posting until enforceability, Sharia/accounting treatment approved | Legal/Sharia/Finance |
| Default/cancellation/refund | Workflow proposal → approval → controlled invoice credits/offsets/refund voucher | Legal/Finance |
| Construction milestone billing | Approved milestone -> controlled Sales Invoice, retention separately reconciled | Finance and Project signoff |
| Expense/subcontractor invoice | Native Purchase Invoice with Project/Cost Center/approved cost code | Finance approval |

**No financial writebacks in v0.1.0**. The `Sidra Installment Line` is intentionally not a subledger and does not represent a collected amount.

### 3.5 CRM / portal / messaging (CRM-01..CRM-09)

Use ERPNext CRM and Customer records as single customer identity; add privacy-aware KYC data and relationship to property contracts and construction projects. A future customer portal must restrict each authenticated person to explicitly authorized agreements and private documents. OTP requires throttling, expiration, anti-enumeration measures, and an approved provider. WhatsApp Business API is a business decision in v1.6; no automated messaging is activated until template approval, consent/opt-out policy, provider integration, and delivery logging.

### 3.6 Dashboards and reports

Executive: units available/reserved/under contract/sold; agreed sales value separated from billed revenue, received cash and outstanding receivables; actual collections vs due; arrears by age; jobs delayed; project commitments and cost; verified cash/ZAAD/eDahab balances. Use ERPNext financial reports for authoritative GL balances; custom dashboards must reconcile to native voucher totals.

## 4. Detailed prototype DocTypes (v0.1.0)

The accompanying app delivers exactly these **10** standard DocType metadata sets:

| DocType | Type | Primary fields | Invariants / integration |
|---|---|---|---|
| `Sidra Scheme` | Master | scheme_code, name, Company, location | Unique scheme code; required Company |
| `Sidra Unit` | Master | unit_code, Scheme, plot boundaries, area, price, status | Unique unit code; status controlled by services |
| `Sidra Reservation` | Document | Unit, Customer, reserved/expires dates, status | One live reservation per unit via row lock; no Payment Entry |
| `Sidra Contract Profile` | Master | terms, legal_hold, due_day, grace, penalty policy fields | One default; B legal hold |
| `Sidra Contract Unit` | Child | unit, allocated_price | Unique per parent contract |
| `Sidra Sale Contract` | Submittable | Customer, Company, profile, unit rows, price, frozen JSON terms | Sum allocations = price; submission locks/allocates units |
| `Sidra Installment Line` | Child | sequence, due_date, amount | Total = signed price minus down payment; generated at submit |
| `Sidra Construction Job` | Document | Customer, ERPNext Project, service, status, stage & BOQ tables | Customer/Project link; no automatic billing |
| `Sidra Project Stage` | Child | milestone, planned/actual dates, completion, billing % | Planning only |
| `Sidra BOQ Line` | Child | cost_code, description, UOM, quantity, rate, calculated amount | Project BOQ preview, not yet revision-controlled |

### 4.1 Future DocTypes (not implemented in prototype)

`Sidra Unit Price History`, `Sidra Contract Party`, `Sidra Contract Clause`, `Sidra Contract Amendment`, `Sidra Title Transfer`, `Sidra Penalty Notice`, `Sidra Payment Allocation` (reference to ERPNext Payment Entry, not cash ledger), `Sidra Settlement Proposal`, `Sidra Contract Cancellation`, `Sidra Inspection Report`, `Sidra BOQ Revision`, `Sidra Variation Order`, `Sidra Retention Certificate`, `Sidra Brokerage Listing`, `Sidra Land Verification`, `Sidra Development Cost Pool`, `Sidra Unit Cost Allocation`, `Sidra Notification Log`. Their workflows/requirements are retained from v1.6 and must be added iteratively.

## 5. Permissions and trust model

- **System Manager:** framework configuration and exception support; all production business approvals must still require an assigned business approver.
- **Sidra Sales User:** read property/catalog, create draft contract; reservation through whitelisted server method only.
- **Sidra Sales Manager:** review property data and submit qualified sales agreements; separate discount/override approval in P1.
- **Sidra Project Manager / Inspector:** construction jobs/stages; inspection/report permissions in P1.
- **Sidra Finance Reviewer:** read contracts; ERPNext Finance posting via native role and approved accounting flow, not custom roles alone.
- **Sidra General Manager:** gated commercial approvals; not a replacement for Finance posting controls.
- **Customer portal:** no access to internal Desk DocTypes in prototype.

Enforce authorization in server-side code and DocType permissions; mere client-side hiding is insufficient. Never expose KYC through unrestricted `frappe.get_all` or public files. Row-level restrictions for branch/Company and contract owners must be added and verified before multi-branch expansion.

## 6. API / event contract (prototype)

| Operation | Method/event | Inputs | Outcomes | Side effects |
|---|---|---|---|---|
| Reserve unit | `sidra_real_estate.services.reservations.reserve_unit` POST | unit_name, customer, days | Reservation ID, expiry | Unit status set Reserved; no cash |
| Expire reservations | Scheduler daily `expire_reservations` | none | Expire stale rows | Release unit only if no live allocation |
| Create contract draft | Frappe Document insert | Customer, Company, profile, unit allocations, price | Frozen profile snapshot | No invoices or payments |
| Submit contract | Frappe Document submit | Existing valid draft | Installment rows generated | Unit status Under Contract; no invoices |
| Create construction job | Frappe Document insert | Customer, Company, optional Project, BOQ/stages | Job record and BOQ total | No certified billing |
| Preview schedule | Pure Python `generate_installments` | Price, down, term, signed_on, grace, due_day | Dated Decimal amounts | None; testable offline |

**Error semantics:** throw on unauthorized user, unknown Customer/Unit, conflicting reservation, duplicate contract units, sum mismatch, blocked profile, incomplete dates, invalid schedule parameters, or crossing legal/Company boundaries. An exception must roll back the entire transactional request.

## 7. Delivery roadmap and dependency sequence

| Release | Scope | Exit gate |
|---|---|---|
| **P0 — Prototype** | 10 DocTypes, Scheme/Unit, atomic reservation, Profile A/B templates, sale contract snapshot, installment generator, construction job/BOQ/stages | Local algorithm tests + real bench install + manual demonstrations |
| **P1 — Commercial MVP** | KYC, price history, bilingual contracts, party/witness/notary templates, overrides/approvals, title tracker, cash/land transaction forms, BOQ revisions, inspections | Sales/Project UAT; legal review |
| **P2 — Finance/Collections** | Voucher mapping, receipts, allocation, advances, customer statements, daily reconciliation, migration of 50–200 contracts, supervised penalties/default proposals | Finance/Sharia/legal policies signed; GL and opening balance reconciliations |
| **P3 — CRM/Portal** | Website lead intake, WhatsApp, OTP customer portal, dashboards and account statements | Security/PII and performance UAT |
| **P4 — Extension** | Brokerage, land verification, full development unit-cost allocation, construction costing/retention, reporting | Production-grade integration/controls |

The v1.6 source anticipated six phases over approximately 23 weeks for a small team. That estimate is **not** a verified ERPNext delivery schedule and must be re-baselined from a full gap assessment and team capacity.

## 8. Non-functional requirements and acceptance standards

- **Security:** TLS, MFA for privileged users, hardened roles, no public KYC files, encrypted backups, secret rotation, audit logs, source-branch protection and security review.
- **Data integrity:** unit reservation locking, immutable term snapshots, submitted/cancelled document controls, idempotent ERPNext integration, bank/mobile-wallet duplicate-reference checks.
- **Performance:** target from v1.6 is under 2 s for common screens with <=50 concurrent users and 10,000 contracts. This remains a **test target**, not an achieved result.
- **Availability:** source target 99% in office hours; specify monitored measurement windows and incident responsibilities before contract sign-off.
- **Recovery:** source daily/off-server backup and quarterly restore test; approve RPO/RTO targets and perform a recorded restore rehearsal.
- **Internationalization:** DD/MM/YYYY display, USD precision, Somali/English templates, `Africa/Mogadishu` timezone, Unicode names, correct right-to-left handling where applicable.
- **Accessibility:** responsive browser UI; allow staff to use standard mobile browsers; no native mobile app in v1.
- **Attachments:** 20 MB source limit, malware scanning or quarantining, restricted file types and download authorization.
- **UAT:** every Must requirement needs linked acceptance scenarios and test evidence. See `ACCEPTANCE-TESTS.md`.

## 9. Known blockers and unresolved decisions

The following must **not** be silently decided by an AI coding agent:

1. Contract B legal title transfer deadline conflicts (14 vs 20 days); Profile B stays blocked.
2. Source v1.6 says buyer late penalties retained as Sidra income, but earlier INS-10 specified charity. Legal/Sharia/Finance must approve enforceability and treatment.
3. The v1.6 Murabaha formula uses a cash offer price minus down payment; this is not the same as asset carrying cost. Approved contract classification and revenue/profit recognition method are required.
4. The source says main accounting ledger undecided. The new architectural recommendation is ERPNext as single ledger, subject to Sidra sign-off.
5. Due date meaning when signing after the chosen day is not explicit. Proposed algorithm begins on the next due day; obtain sign-off.
6. Whether an unsigned draft may lock a plot, and whether contract submission alone is sufficient to mark `Under Contract` without signed-copy validation, must be agreed. Prototype uses submission only; no legal transfer.
7. The source does not cover leasing. It remains out of scope unless formally added.
8. Historical 50–200 contract migration requires contract-by-contract reconciliation of signed price, collected cash and outstanding amounts before ERPNext posting.
9. Customer-specific source details are omitted from this version; no live personal data belongs in repository fixtures or demos.

## 10. Verification, repository and change control

- GitHub repository owned by Sidra; Claude Code implements PRs against the versioned SRS, ChatGPT independently reviews requirements and business control compliance, Sidra approves merges/releases.
- Document all source requirement IDs in `REQUIREMENTS-TRACEABILITY.csv` with delivery status and evidence.
- CI validates pure business rules and JSON metadata. **CI does not replace a full ERPNext bench installation or integration tests.**
- PR template: requirement IDs, screenshots/recording, migrations, access-control impact, positive/negative tests, accounting impact and reversal plan.
- Release process: staging test, security review, UAT sign-off, backup, tagged release, controlled deployment, smoke tests, rollback plan.
- A v2.0 **approved** SRS is only issued after management, Finance and legal/Sharia gates are resolved or explicitly accepted as exclusions.

## Appendix — Source-related corrections

- v1.6's target platform section (Laravel/MySQL/Filament, queue, authorization packages) is superseded by Frappe/ERPNext architecture.
- All custom tables for customers/invoices/payments/journal entries are superseded by native ERPNext DocTypes; new Sidra DocTypes are reserved for industry domain data.
- The original source's claim that the source names are placeholders should not be taken as anonymization for software fixtures; the repository uses synthetic demo names only.
- No AI-authored spec or code constitutes a legal, Sharia, accounting or security certification.
