# Sidra Real Estate on ERPNext — Requirements Mapping v0.1

| Field | Value |
| --- | --- |
| Document | ERPNext mapping for SREMS-SRS v1.6 |
| Version | v0.1 (Draft) |
| Date | 5 Nov 2026 |
| Prepared by | Mohamoud Abdullahi Sheikh |
| Platform | ERPNext v16 + Frappe Framework v16 (branch `version-16`) |
| Custom app | `sidra_realestate` (this repository) |

This document replaces section 11 (Technical architecture) of [SREMS-SRS_v1.6.md](SREMS-SRS_v1.6.md). The business requirements in that spec are unchanged; this file says which ERPNext feature covers each one and what the custom app adds.

**Rule:** use standard ERPNext wherever it fits, and add custom DocTypes only for what ERPNext has no concept of (plots, contract profiles, title transfer, brokerage). Never edit ERPNext core; all changes live in this app as DocTypes, Custom Fields, Property Setters, hooks and fixtures, so ERPNext can be upgraded safely.

## 1. Platform

| Item | Choice |
| --- | --- |
| ERPNext / Frappe | v16, branch `version-16` |
| Python | 3.14 |
| Node.js | 24 |
| Database | MariaDB 11.8 |
| Cache / queue | Redis 6+ |
| PDF | wkhtmltopdf 0.12.6 (patched Qt) |
| Hosting | Cloud VPS, Ubuntu 24.04, production setup via `bench setup production` or frappe_docker |

## 2. Requirement map

### 2.1 Customers and CRM (spec section 7)

| Spec item | ERPNext standard | Custom in `sidra_realestate` |
| --- | --- | --- |
| Leads, sources, stages, lost reason (CRM-01, 02) | Lead, Opportunity, Lead Source, Lost Reason | — |
| Site visits, follow-ups (CRM-03) | Event / ToDo linked to Lead | — |
| Customer profile, KYC (CRM-04, SAL-07) | Customer, Contact, Address, File attachments | Custom Fields on Customer: national ID, ID document, guarantor name / phone |
| Duplicate check on phone / ID (CRM-05) | — | `validate` hook on Customer |
| Customer portal (CRM-06) | Frappe portal, Website User | Portal pages: my contracts, schedule, statement, receipts |
| Message templates EN / SO (CRM-08) | Notification, Email Template | WhatsApp templates (see 2.7) |

### 2.2 Property inventory and sales (spec section 4)

| Spec item | ERPNext standard | Custom in `sidra_realestate` |
| --- | --- | --- |
| Schemes, blocks (SAL-01) | — | DocType **Sidra Scheme** |
| Plots and houses (SAL-01, SAL-12, SAL-14) | Item (non-stock) per unit, used on invoices | DocType **Sidra Property Unit**: scheme, block, number, type, size, plot fraction (full / half), district, neighbourhood, land parcel (Beerta), four boundaries, off-plan status, delivery date, expansion phase, status, title deed no.; creates / links its Item |
| Price list with history (SAL-02) | Price List, Item Price (valid from) | — |
| Availability grid / map (SAL-03) | — | Page **Unit Availability** |
| Reservation with deposit and expiry (SAL-04) | Payment Entry (advance) | DocType **Sidra Reservation**; daily scheduler expires it |
| Sale quotation cash vs installment (SAL-05) | Quotation | Print Format showing both options |
| Sale contract, several plots, parties, notary (SAL-06, 13, 19) | — | Submittable DocType **Sidra Sale Contract** with child tables **Sidra Contract Unit** and **Sidra Contract Party** (buyer, buyer agent, seller, seller guarantor, witnesses); notary name, reference, date; signed scan |
| Clause library (SAL-20) | — | DocType **Sidra Contract Clause** (text_so, text_en) |
| Title transfer and deadline (SAL-08, SAL-18) | — | DocType **Sidra Title Transfer** with deadline, delay-penalty calculation, alerts |
| Cancellation, refund (SAL-09) | Sales Invoice return (Credit Note), Payment Entry (pay) | Cancel action on contract |
| Commission (SAL-11) | Sales Partner, commission rate | — |
| Brokerage listings, verification (SAL-15, 16) | Sales Invoice for fees | DocTypes **Sidra Brokerage Listing**, **Sidra Verification Request** |

### 2.3 Installments and collections (spec section 5)

| Spec item | ERPNext standard | Custom in `sidra_realestate` |
| --- | --- | --- |
| Contract profiles and per-contract override (INS-18 to INS-21, section 5.5) | — | DocType **Sidra Contract Profile** (all settings in 5.5); contract copies them into a frozen terms snapshot; override needs Sales Manager approval (Workflow) |
| Murabaha pricing (5.1) | — | Python service `installments/pricing.py` |
| Schedule generation (INS-02, 13, 14) | Payment Terms Template / Payment Schedule on Sales Invoice | On contract submit: create one Sales Invoice for the contract price with a generated Payment Schedule (grace months, due day, rounding on last installment) |
| Profit recognition | Sales Invoice Item **deferred revenue** | Murabaha profit posted as a separate invoice line with deferred revenue over the term |
| Receipts by cash / bank / ZAAD / eDahab (INS-04, INS-17) | Payment Entry, Mode of Payment (one per channel, each with its own account) | Receipt Print Format; WhatsApp receipt |
| Oldest-first allocation, partial and advance (INS-05) | Payment Entry allocation against Payment Schedule | — |
| Reminders and overdue (INS-07) | Notification (days before / after due date) | WhatsApp channel |
| Aging (INS-08) | Accounts Receivable report (ageing buckets) | — |
| Late penalty with notice (INS-10, INS-15) | Dunning, Dunning Type | DocType **Sidra Penalty**; creates a Sales Invoice to Penalty income (or charity account, per profile) |
| Default and refund less retained charge (INS-11, INS-16) | Credit Note + Payment Entry | Scheduler flags contracts after N consecutive missed installments; cancellation workflow |
| Early settlement rebate (INS-09) | — | Rebate action on contract, GM approval, posts a Credit Note against deferred profit |

### 2.4 Construction projects (spec section 3)

| Spec item | ERPNext standard | Custom in `sidra_realestate` |
| --- | --- | --- |
| Full build / design / inspection jobs (3.1) | Project, Project Type, Project Template (stage list as tasks) | Three Project Templates seeded as fixtures |
| Quotation from BOQ (CON-02) | Quotation with items | BOQ item group and Print Format |
| Contract with milestones (CON-03, CON-07) | Sales Order + Payment Schedule; Sales Invoice per milestone | Link milestone to Task completion |
| Retention (CON-11) | — | Custom Fields on Sales Invoice: retention %, retention amount; posting to Retention receivable |
| Stages, planned vs actual, Gantt (CON-04, CON-12) | Task, Project Gantt view | — |
| Site inspections (CON-05) | — | DocType **Sidra Site Inspection** (checklist child table, photos, findings) |
| Variation orders (CON-06) | Sales Order amendment | DocType **Sidra Variation Order** linked to Project |
| Project costs, budget vs actual (CON-08) | Purchase Invoice / Expense Claim with Project, Budget, Project costing | — |
| Site diary (CON-10) | — | DocType **Sidra Site Diary** |
| Beacon / foundation job at lowest of 3 quotes (CON-13) | Supplier Quotation comparison | Check on the job's Quotation |
| Land sale creates design-and-build lead (CON-14) | Lead | Hook on Sale Contract submit |

### 2.5 Finance and accounting (spec section 6)

All of section 6 runs on ERPNext Accounts: Chart of Accounts, Journal Entry, Payment Entry, bank reconciliation, period closing, Trial Balance, P&L, Balance Sheet, General Ledger. The custom app seeds the extra accounts as fixtures: Murabaha receivable, Deferred Murabaha profit, Murabaha profit income, Penalty income, Charity payable, Customer deposits, Retention receivable, Title delay penalty expense, Cancellation charge income, Brokerage commission income, Verification fee income, Land / housing inventory, Cost of property sold.

Whether ERPNext is Sidra's main ledger is still open (spec section 13); ERPNext can do both, so this does not block development.

### 2.6 Reports and dashboards (spec section 8)

| Spec item | ERPNext standard | Custom |
| --- | --- | --- |
| Sales, collections, aging, P&L, cash | Standard reports + Dashboard Charts + Number Cards | Workspace **Sidra Real Estate** |
| Inventory by scheme, due list, defaulted contracts, title deadlines, deferred profit | — | Script Reports in this app |

### 2.7 Messaging

WhatsApp Business API was chosen. ERPNext has no built-in WhatsApp sender, so the options are a community app (for example `frappe_whatsapp`) or a small connector in this app. To decide in Phase 4 after testing with Sidra's WhatsApp Business account.

### 2.8 Security and audit (spec section 10)

| Spec item | Frappe standard |
| --- | --- |
| Roles and permissions (section 2) | Role, Role Profile, DocType permissions, User Permissions |
| Audit trail (NFR-03) | Track Changes (Version), Activity Log, Access Log |
| No delete of financial records (NFR-04) | Submittable documents: cancel and amend only |
| Backups (NFR-05) | Scheduled backups + offsite (S3-compatible) |
| Two-factor login (NFR-01) | System Settings: two-factor authentication |

## 3. Roles

Seeded as fixtures: Sidra General Manager, Sidra Project Manager, Sidra Engineer, Sidra Sales Officer, Sidra Sales Manager, Sidra Cashier, Sidra Accountant. System Administrator and Customer use the standard Frappe roles.

## 4. App modules

| Module (folder) | Holds |
| --- | --- |
| Sidra Property (`sidra_property`) | Scheme, Property Unit, Reservation, Title Transfer |
| Sidra Sales (`sidra_sales`) | Sale Contract, Contract Unit, Contract Party, Contract Clause |
| Sidra Installments (`sidra_installments`) | Contract Profile, Penalty, pricing and schedule services |
| Sidra Construction (`sidra_construction`) | Site Inspection, Variation Order, Site Diary |
| Sidra Brokerage (`sidra_brokerage`) | Brokerage Listing, Verification Request |

## 5. Build order

Same phases as spec section 12, on ERPNext:

| Phase | Release | Scope |
| --- | --- | --- |
| 0 | v0.1.0 | Bench and site, this app installed, roles, accounts, Modes of Payment |
| 1 | v0.2.0 | Property, Sales and Installments modules; contract print format in Somali |
| 2 | v0.3.0 | Construction module on Project / Task |
| 3 | v0.4.0 | Reports, workspace, dashboards |
| 4 | v0.5.0 | Portal, WhatsApp |
| 5 | v1.0.0 | Import of 50–200 live contracts from Excel, UAT, go-live |
