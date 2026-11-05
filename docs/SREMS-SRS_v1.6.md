# Sidra Real Estate Management System — Requirements Specification v1.6

> **Platform note (5 Nov 2026):** after this spec was written, Sidra chose **ERPNext v16 (Frappe Framework)** instead of Laravel + MySQL. Section 11 (Technical architecture) is superseded by [docs/ERPNEXT-MAPPING_v0.1.md](ERPNEXT-MAPPING_v0.1.md). All business requirements still apply.


Nov 5, 2026 · @moi

## Document control

This is version 1.6, the seventh draft for review by Sidra Real Estate management before development starts.

| Field | Value |
| --- | --- |
| Document | Sidra Real Estate Management System (SREMS) — Software Requirements Specification |
| Document ID | SREMS-SRS |
| Version | v1.6 (Draft) |
| File name on export | SREMS-SRS\_v1.6.docx / SREMS-SRS\_v1.6.pdf |
| Prepared by | Mohamoud Abdullahi Sheikh |
| Prepared for | Sidra Real Estate management |
| Target platform | PHP / Laravel + MySQL web application |

Version rule: every change approved by Sidra raises the minor number (v1.1, v1.2). Sign-off of the full scope raises it to v2.0, the baseline that development is measured against.

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| v1.0 | 5 Nov 2026 | First draft: all five modules, data model, architecture, phases | Mohamoud Abdullahi Sheikh |

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| v1.6 | 5 Nov 2026 | Real customer names replaced with placeholders (Contract A, Contract B); both contracts treated as valid templates with flexible payment terms; profiles renamed Profile A and Profile B | Mohamoud Abdullahi Sheikh |
| v1.5 | 5 Nov 2026 | Hagbad full plot set to Profile A: $11,000 over 14 months, no down payment; open items down to 2 | Mohamoud Abdullahi Sheikh |
| v1.4 | 5 Nov 2026 | Section 13 answered: 18 decisions recorded (payments, messaging, penalties, hosting, billing, brokerage, off-plan); 3 items still open | Mohamoud Abdullahi Sheikh |
| v1.3 | 5 Nov 2026 | Added 5.5: every contract term configurable through contract profiles (Profile A, Profile B) with per-contract override | Mohamoud Abdullahi Sheikh |
| v1.2 | 5 Nov 2026 | Contract A made the default: default penalty, default rule, due day and title deadline taken from it; three open questions closed | Mohamoud Abdullahi Sheikh |
| v1.1 | 5 Nov 2026 | Checked against sidrahomes.co and two land sale contracts: added 1.4, 3.4, 4.4, 5.4, 6.3, new data tables and open questions | Mohamoud Abdullahi Sheikh |

## 1. Purpose and scope

SREMS is one web system that runs Sidra's two businesses: construction services for clients, and the sale of Sidra's own land and houses for cash or on Murabaha installments. It tracks every job, plot, contract, payment and receivable in one place and feeds the accounts automatically.

### 1.1 Business lines covered

| Business line | What Sidra sells | How the client pays |
| --- | --- | --- |
| Full construction | Design + build to handover on the client's land | Contract price billed by stage (milestones) |
| Design only | Architectural / structural drawings, BOQ, permit drawings | Fixed fee, usually deposit + balance on delivery |
| Inspection only | Site inspection, supervision visits, structural or handover reports | Fee per visit or per report |
| Land sales | Plots from Sidra land schemes | Cash, or Murabaha installments |
| House sales | Completed or off-plan houses / units | Cash, or Murabaha installments |

### 1.2 In scope

- Construction project management: quotation, contract, stages, BOQ, inspections, progress billing
- Property inventory: schemes, plots, houses, prices, availability
- Sales: reservation, cash sale, Murabaha installment sale, contract printing, title transfer tracking
- Collections: installment schedules, receipts, overdue follow-up, statements
- Finance: client and customer ledgers, cash and bank, general ledger postings, Murabaha profit recognition
- CRM: leads, enquiries, site visits, customer self-service portal, SMS / WhatsApp / email notifications
- Reports and management dashboards

### 1.3 Out of scope for v1

- Payroll and HR
- Full procurement / inventory of construction materials (only material costs per project are recorded)
- CAD or drawing tools (drawings are uploaded as files)
- Mobile apps (the web system is mobile-responsive instead)

### 1.4 What the website and contracts confirm (added in v1.1)

Sidra's website and two signed land sale contracts confirm the core scope. They change four things: contracts are Somali-language notarised agreements; installments are a single agreed price rather than an itemised markup; late penalties go both ways; and land brokerage is a service in its own right. Sources: [sidrahomes.co](https://www.sidrahomes.co/), the [Hagbad land offer](https://www.sidrahomes.co/hagbad-land-offer-masalaha/), [land brokerage](https://www.sidrahomes.co/land-brokerage/), and two Sidra land sale contracts, called Contract A (customer: Ayaan Cali Warsame) and Contract B (customer: Cabdiraxmaan Yuusuf Jaamac) in this document; the customer names are placeholders. Both contracts are valid templates: payment terms are flexible and set per contract, with Contract A's terms as the system default.

| Finding | Source | Effect on the system |
| --- | --- | --- |
| Sidra Homes offers land brokerage, architecture & design, residential developments and off-plan housing; head office Miiska Saraakiisha, Pepsi Road, Hargeisa | Website | Brokerage added as a business line (SAL-15 to SAL-17) |
| Projects: Berbera Townhouses (3-bed, from $119,000, off-plan), Rayan Gardens (3–4-bed villas, Hargeisa), Safa Housing (expandable 2–4-bed homes) | Website | Units need off-plan status, delivery date and expansion phase (SAL-14) |
| Hagbad offer, East Masalaha: 9×24 m half plot $5,500 at $250/month for 22 months; full plot $11,000; no interest; buyers may pay faster at any time | Website | Plans with no markup, half / full plots, early payment without penalty (INS-13) |
| Contracts sell 18×24 m plots identified by district (M/Haybe), neighbourhood (Masalaha), original land parcel (Beerta Ilma Saleeban Bide) and four boundaries | Contracts | New unit fields (SAL-12) |
| One contract can cover two plots; buyer may act through an agent (wakiil) | Contract A | Multi-unit contracts and buyer agent (SAL-13) |
| $9,000 price: $3,000 at signing, $6,000 as 24 × $250, first due 3 months after signing, by the 10th of each month | Contract B | Grace period and due day per contract (INS-14) |
| $14,000 price: 14 × $1,000, no down payment, by the 5th of each month | Contract A | Down payment can be zero (INS-14) |
| Buyer late penalty: $5 a day, $150 a month (Contract A); Contract B uses $100 after a 15-day written notice | Contracts | Configurable penalty rules (INS-15) |
| Two consecutive missed months cancels the contract; money refunded less one month ($1,000) | Contract A | Default and refund workflow (INS-16) |
| Sidra must issue the title within 20 days of final payment or pay the buyer $5 a day (Contract A); Contract B adds $220 a month and a refund + 10% after 90 days | Contracts | Title deadline tracking (SAL-18) |
| Seller's guarantor, two witnesses and Islaax Public Notary sign every contract | Contracts | Contract parties and notary details (SAL-19) |
| Sidra builds plot beacons / foundation at lowest market price (3 independent quotes) and has first right to design and build | Contracts | Land sales feed construction leads (CON-13, CON-14) |
| Construction and inspection services are not described on the website | Website | Kept in scope as you confirmed; check pricing with Sidra (section 13) |

## 2. User roles and permissions

Nine roles cover the system; each user gets one or more roles, and every action is checked against them. Approvals that move money or ownership (discounts, contract approval, early settlement waivers, title transfer) need a second person.

| Role | Main tasks | Can approve |
| --- | --- | --- |
| System Administrator | Users, roles, settings, backups, audit log | — |
| General Manager | Dashboards, all reports, final approvals | Contracts above limit, discounts, write-offs, title transfer |
| Project Manager | Construction projects, stages, BOQ, progress | Stage completion, variation orders |
| Engineer / Inspector | Site visits, inspection reports, photos, snag lists | Inspection reports |
| Sales Officer | Leads, reservations, sale quotations, Murabaha proposals | — |
| Sales Manager | Price lists, reservations, sales contracts | Reservations, discounts within limit, sale contracts |
| Cashier | Receive payments, print receipts | — |
| Accountant | Invoices, journal entries, reconciliation, collections | Receipts reversal, period close |
| Customer (portal) | View own contracts, schedule, statement; download receipts and documents | — |

Permissions are set per screen and per action (view, create, edit, approve, delete, export). Delete is replaced by cancel-with-reason for any financial record.

## 3. Module 1 — Construction Projects

Every construction job, whatever its type, follows one record from enquiry to closure; the service type decides which stages, documents and billing rules apply.

### 3.1 Service types

| Type | Stages | Billing | Key output |
| --- | --- | --- | --- |
| Full construction | Site survey → Design → Permit → Foundation → Structure → Roofing → Finishing → Handover → Defects period | Milestone invoices against contract value; retention held until end of defects period | Handover certificate |
| Design only | Brief → Concept → Detailed drawings → BOQ → Delivery | Deposit + balance on delivery | Drawing set, BOQ |
| Inspection only | Request → Scheduled visit → Report → Delivery | Fee per visit or per report | Signed inspection report |

Stages are templates the administrator can edit; a project copies the template when it is created and can then be adjusted.

### 3.2 Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| CON-01 | Register a client (individual or company) and the site: location, plot number, GPS, title deed reference | Must |
| CON-02 | Create a quotation from a BOQ (items, quantity, unit, rate, amount) or a fixed fee; print it in Sidra letterhead | Must |
| CON-03 | Convert an approved quotation into a contract with value, start date, duration, payment milestones and retention % | Must |
| CON-04 | Track each stage: planned vs actual dates, % complete, responsible engineer, status | Must |
| CON-05 | Record site inspections: date, inspector, checklist results, photos, defects found, next action | Must |
| CON-06 | Raise variation orders that change the contract value, with client approval recorded | Must |
| CON-07 | Generate milestone invoices when a stage is signed off; post them to the client ledger | Must |
| CON-08 | Record project costs (materials, labour, subcontractors, equipment) against BOQ lines to show budget vs actual and margin | Should |
| CON-09 | Store documents per project: drawings, permits, contracts, reports (PDF, DWG, images) | Must |
| CON-10 | Daily site diary: weather, workers on site, work done, issues | Could |
| CON-11 | Snag list at handover; release retention when snags are cleared and defects period ends | Should |
| CON-12 | A Gantt-style project timeline and an alert when a stage passes its planned end date | Should |

### 3.3 Project statuses

Enquiry → Quoted → Contracted → In progress → On hold → Completed → Defects period → Closed, plus Cancelled from any status before Completed.

### 3.4 Additions from the land contracts (v1.1)

| ID | Requirement | Priority |
| --- | --- | --- |
| CON-13 | Beacon / foundation job for a land buyer: record at least 3 independent quotes and price Sidra's job at the lowest; if the buyer chooses another contractor, record that and close the lead | Must |
| CON-14 | Every land sale creates a design-and-build lead for the buyer, because Sidra has first right to design and build on the plot; the buyer may decline without giving a reason | Should |
| CON-15 | Design jobs check the plan against the neighbourhood master design and its restrictions (no garages, slaughter places or fuel stations) | Could |

## 4. Module 2 — Property Inventory and Sales

Every plot and house Sidra sells is a numbered unit with one status at a time, so no unit can be sold twice and management always sees what is left to sell.

### 4.1 Inventory structure

Scheme (e.g. a land subdivision or housing estate) → Block / Phase → Unit (plot or house). Each unit holds: unit number, type (plot / house / apartment), size (m²), dimensions, bedrooms and floors for houses, corner or main-road flag, title deed reference, cash price, photos, and a position on the scheme map.

### 4.2 Unit statuses

Available → Reserved (time-limited, default 7 days) → Sold-Installment or Sold-Cash → Title transferred. A reservation that expires without a contract returns the unit to Available automatically; Blocked is used for units withheld by management.

### 4.3 Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| SAL-01 | Create schemes, blocks and units; import units in bulk from Excel | Must |
| SAL-02 | Keep a price list per scheme with effective dates; price history is never overwritten | Must |
| SAL-03 | Show a colour-coded availability grid / map per scheme (available, reserved, sold) | Must |
| SAL-04 | Reserve a unit for a customer with a reservation deposit and expiry date | Must |
| SAL-05 | Prepare a sale quotation for cash or installment, showing both options side by side | Must |
| SAL-06 | Approve and print the sale contract (cash sale or Murabaha sale) from a template, in English and Somali | Must |
| SAL-07 | Record the buyer's KYC: national ID / passport, phone, address, guarantor details, scanned copies | Must |
| SAL-08 | Track title transfer: documents required, submission to the land office, deed number, date handed to customer | Must |
| SAL-09 | Handle cancellation and refund: cancellation fee rule, refund amount, unit returned to Available | Should |
| SAL-10 | Transfer a contract to another buyer (resale before full payment) with fee and approval | Could |
| SAL-11 | Record sales commission per agent / officer | Could |

Title passes only when the contract is fully paid, unless the General Manager approves an earlier transfer with a recorded security.

### 4.4 Additions from the website and land contracts (v1.1)

The sale contract is printed as Sidra's Somali-language agreement, notarised at Islaax Public Notary. The system fills it from the contract record; clause wording is kept in an editable template.

| ID | Requirement | Priority |
| --- | --- | --- |
| SAL-12 | Plot fields: district (Degmada), neighbourhood (Xaafada), original land parcel (Beerta), plot size (e.g. 18×24 m, half plot 9×24 m), and the four boundaries (Bari / Waqooyi / Koonfur / Galbeed: road or building) | Must |
| SAL-13 | One contract can cover several plots; the buyer may sign through an agent (wakiil) whose name and phone are recorded | Must |
| SAL-14 | House units carry off-plan status, estimated delivery date and expansion phase (e.g. Safa: 1-storey 2-bed → 2-storey → 3-storey 4-bed) | Must |
| SAL-15 | Brokerage listings: plots sold for third-party owners, with owner details, asking price, commission and listing status, kept apart from Sidra's own stock | Must |
| SAL-16 | Land verification service: request, documents checked, legal vetting result, report, fee, and a 2–7 day turnaround alert | Should |
| SAL-17 | Listing page per location (Hargeisa, Berbera, Hagbad Masalaha) fed from available units and brokerage listings | Could |
| SAL-18 | Title deadline: count 20 days from final payment, alert before it passes, and calculate Sidra's delay penalty at $5 a day; the 90-day refund + 10% from Contract B is an optional clause | Must |
| SAL-19 | Contract parties and notarisation: seller (company owner), seller's guarantor with the property pledged, two witnesses with phones, notary name, notary reference (format IPN/HL/NNN/YYYY) and signing date; scan of the signed copy attached | Must |
| SAL-20 | Contract clauses library in Somali (and English): neighbourhood restrictions, insolvency protection for the buyer, title costs paid by buyer, first right to design and build; clauses chosen per contract | Must |

## 5. Module 3 — Murabaha Installments and Collections

Installment sales use Murabaha: Sidra sells the unit at its cost-plus price with a profit amount fixed on the day of the contract, and the customer pays it in equal monthly installments. The profit never grows with time or late payment; the system locks it when the contract is approved.

### 5.1 Pricing formula

The sales officer enters the cash price, down payment, markup rate and number of months; the system calculates the rest.

```latex
\begin{aligned}
F &= P - D \\
\text{Profit} &= F \times r \times \tfrac{n}{12} \\
S &= P + \text{Profit} \\
M &= \frac{F + \text{Profit}}{n}
\end{aligned}
```

P = cash price, D = down payment, F = amount financed, r = annual markup rate set by management, n = number of months, S = Murabaha sale price written in the contract, M = monthly installment. Installments are rounded to the whole dollar and the last installment absorbs the rounding difference.

### 5.2 Worked example

| Item | Value |
| --- | --- |
| Plot cash price (P) | $30,000 |
| Down payment 30% (D) | $9,000 |
| Amount financed (F) | $21,000 |
| Markup rate (r), term (n) | 10% a year, 24 months |
| Murabaha profit | $21,000 × 10% × 2 = $4,200 |
| Murabaha sale price (S) | $34,200 |
| Monthly installment (M) | ($21,000 + $4,200) ÷ 24 = $1,050 |
| Each installment split | $875 cost recovery + $175 profit |

### 5.3 Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| INS-01 | Configure Murabaha plans: minimum down payment %, allowed terms (e.g. 6–60 months), markup rate per term, per scheme or unit type | Must |
| INS-02 | Generate the installment schedule on contract approval: due dates, amount, cost and profit split per installment | Must |
| INS-03 | Lock the sale price and profit after approval; any change needs a formal rescheduling with GM approval and a new schedule version | Must |
| INS-04 | Receive payments by cash, bank transfer or mobile money (ZAAD, eDahab); print / SMS a numbered receipt | Must |
| INS-05 | Allocate each payment to the oldest unpaid installment first; allow partial and advance payments | Must |
| INS-06 | Show each contract's status: current, overdue (days and amount), fully paid, rescheduled, defaulted, cancelled | Must |
| INS-07 | Send reminders 5 days before due, on the due date, and at 7 and 30 days overdue by SMS / WhatsApp / email | Must |
| INS-08 | Aging report of arrears in 1–30, 31–60, 61–90 and 90+ day buckets per officer and scheme | Must |
| INS-09 | Early settlement: show the outstanding amount and an optional profit rebate (ibra') that management may grant; the rebate is never automatic | Must |
| INS-10 | Late payment charge, if Sidra uses one, is posted to a charity account, not to income | Should |
| INS-11 | Flag a contract for default review after a configurable number of missed installments (default 2, per Contract A) | Should |
| INS-12 | Customer statement and full schedule printable or downloadable from the portal at any time | Must |

Sidra's Sharia adviser should confirm the plan settings, rebate policy and late-payment rule before go-live.

### 5.4 How Sidra's contracts actually work (v1.1)

Both contracts state one agreed price and split it into equal months; they show no separate markup. So the system keeps the Murabaha formula in 5.1 but allows a markup of zero, and stores the cash price beside the contract price so any profit inside the price can still be reported. Both are valid templates; Contract A's terms are the system default and every term can be changed per contract (see 5.5).

| Item | Contract B | Contract A |
| --- | --- | --- |
| Agreed price | $9,000 (1 plot, 18×24 m) | $14,000 (2 plots, 18×24 m each) |
| Down payment | $3,000 at signing | None |
| Installments | 24 × $250 = $6,000 | 14 × $1,000 = $14,000 |
| First installment | 3 months after signing | From the signing month |
| Due day | By the 10th of each month | By the 5th of each month |
| Buyer late penalty | $100 after a 15-day written notice | $5 a day ($150 a month) |
| Default | Not stated | 2 consecutive missed months: contract cancelled, refund less $1,000 |
| Sidra's title deadline | 20 days in clause 4 but 14 days in clause 6 (conflict to fix); $220 a month late; refund + 10% after 90 days | 20 days after final payment; $5 a day late |

| ID | Requirement | Priority |
| --- | --- | --- |
| INS-13 | Plans with zero markup (Hagbad style); early or extra payments reduce the remaining months or the last installments, with no penalty | Must |
| INS-14 | Per contract: down payment may be zero, grace period before the first installment (e.g. 3 months), and due day of the month (default 5th, per Contract A) | Must |
| INS-15 | Penalty rules per contract: fixed amount after N days' written notice, or an amount per day with a monthly cap (default $5 a day, capped at $150 a month, per Contract A); the system prints the notice and records the date it was served | Must |
| INS-16 | Default rule per contract: N consecutive missed months (default 2, per Contract A) triggers cancellation review; the refund is calculated as paid amount less the retained charge (default one monthly installment; $1,000 in Contract A), and the plots return to Available after approval | Must |
| INS-17 | Payment references show which Sidra account or mobile-money number received the money | Must |

The contracts treat the buyer's late penalty as Sidra's money, which conflicts with INS-10 (penalty to a charity account). Decided in v1.4: penalties stay as Sidra's income; the charity option remains available as a setting.

### 5.5 Configurable contract terms (v1.3)

Every term where the two contracts differ is a setting, not code. Terms are grouped into named contract profiles: the system ships with "Profile A" (from Contract A) as the default and "Profile B" (from Contract B), and management can add more. A new contract copies its profile's values; the sales officer can change them on that contract, and any change from the profile needs Sales Manager approval and is recorded in the audit log.

| Setting | Options | Profile A (default) | Profile B |
| --- | --- | --- | --- |
| Down payment | None, fixed amount, or % of price | None | $3,000 at signing |
| Number of installments | 1–60 months | 14 | 24 |
| Grace period before first installment | 0–12 months | 0 | 3 months |
| Due day of month | 1–28 | 5th | 10th |
| Markup | 0% or a rate (see 5.1) | 0% (single agreed price) | 0% (single agreed price) |
| Buyer late penalty type | None, per day with monthly cap, or fixed after written notice | Per day with cap | Fixed after notice |
| Penalty amount | Amount per day / cap, or fixed amount | $5 a day, $150 a month cap | $100 |
| Written notice period before penalty | 0–60 days | 0 | 15 days |
| Penalty goes to | Penalty income or charity account | Penalty income | Penalty income |
| Default trigger | N consecutive missed installments, or off | 2 | Off (not stated) |
| Refund on default | Paid amount less: one installment, fixed amount, or % | Less one installment ($1,000) | Not stated |
| Title deadline after final payment | Days | 20 | 20 or 14 (contract text conflicts) |
| Sidra's title delay penalty | None, per day, or per month | $5 a day | $220 a month |
| Buyer's refund right if title is late | Off, or after N days with X% compensation | Off | After 90 days, refund + 10% |
| Early payment | Allowed without penalty / shortens term / reduces last installments | Allowed, reduces last installments | Allowed, reduces last installments |
| Optional clauses | Neighbourhood restrictions, insolvency protection, beacon / foundation at lowest quote, first right to design and build | Restrictions, beacon, first right | All four |

| ID | Requirement | Priority |
| --- | --- | --- |
| INS-18 | Contract profiles: create, edit, activate and retire profiles holding every setting above; one profile is the default | Must |
| INS-19 | Per-contract override of any setting, with approval and audit trail; the printed contract and the schedule use the contract's own values | Must |
| INS-20 | Changing a profile never changes contracts already signed; each contract keeps a frozen copy of its terms | Must |
| INS-21 | Contract template prints only the clauses and values switched on for that contract, in Somali and English | Must |

Hagbad Round 2 full plot (9×24 m × 2, $11,000, East Masalaha) uses Profile A, decided 5 Nov 2026: no down payment, 14 monthly installments of $786 with a last installment of $782, due by the 5th, $5 a day late penalty capped at $150 a month, cancellation after 2 consecutive missed months with a refund less one installment, and title within 20 days of final payment. The half plot keeps its published plan of $250 a month for 22 months.

## 6. Module 4 — Finance and Accounting

Every operational event (contract, invoice, receipt, cost) creates its journal entry automatically, so the general ledger is always in step with sales and projects; accountants post only manual adjustments. Murabaha profit sits in a deferred account and moves to income one installment at a time.

### 6.1 Automatic postings

Amounts use the worked example in 5.2 where it applies.

| Event | Debit | Credit |
| --- | --- | --- |
| Reservation deposit received | Cash / Bank | Customer deposits (liability) |
| Cash sale of a unit | Cash / Bank | Property sales revenue |
| Murabaha contract approved | Cash / Bank $9,000 (down payment) + Murabaha receivable $25,200 | Property sales revenue $30,000 + Deferred Murabaha profit $4,200 |
| Cost of the unit sold (any sale) | Cost of property sold | Land / housing inventory |
| Installment received | Cash / Bank $1,050 | Murabaha receivable $1,050 |
| Profit earned on that installment | Deferred Murabaha profit $175 | Murabaha profit income $175 |
| Early settlement rebate (ibra') | Deferred Murabaha profit | Murabaha receivable |
| Late payment charge (if used) | Cash / Bank | Charity payable |
| Construction milestone invoice | Client receivable (net) + Retention receivable | Construction revenue |
| Design or inspection fee invoice | Client receivable | Design / inspection fee revenue |
| Client payment received | Cash / Bank | Client receivable |
| Project cost recorded | Project cost (by project and BOQ line) | Cash / Bank or Supplier payable |

### 6.2 Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FIN-01 | Chart of accounts with assets, liabilities, equity, revenue and expense groups; seeded with the accounts in 6.1 | Must |
| FIN-02 | Posting rules held in a settings table so the accountant can map each event to accounts without code changes | Must |
| FIN-03 | Cash and bank accounts, including mobile-money wallets; daily cashier closing with cash count | Must |
| FIN-04 | Bank reconciliation by statement import (CSV / Excel) | Should |
| FIN-05 | Manual journal entries with approval; posted entries can only be reversed, never edited | Must |
| FIN-06 | Trial balance, profit and loss, balance sheet, general ledger and account statements for any date range | Must |
| FIN-07 | Monthly period close that blocks back-dated postings | Should |
| FIN-08 | Supplier payables for project costs: supplier bills, payments, supplier statements | Should |
| FIN-09 | Export journals to Excel and to an external accounting package if Sidra keeps one | Could |
| FIN-10 | Base currency USD with optional Somaliland Shilling receipts converted at the day's rate | Should |

### 6.3 Extra postings from the contracts and brokerage (v1.1)

| Event | Debit | Credit |
| --- | --- | --- |
| Buyer late penalty collected | Cash / Bank | Penalty income or Charity payable (setting, see 5.4) |
| Title delay penalty owed to buyer | Title delay penalty expense | Customer payable (or reduce receivable) |
| Contract cancelled on default | Property sales revenue (reversal) + Land inventory (unit returned) | Murabaha / installment receivable + Cost of property sold (reversal) |
| Refund to buyer less retained charge | Customer payable | Cash / Bank (refund) + Cancellation charge income (e.g. $1,000) |
| Brokerage sale closed | Commission receivable | Brokerage commission income |
| Verification service fee | Client receivable | Verification fee income |

## 7. Module 5 — CRM, Customer Portal and Notifications

One customer record serves both businesses: a person who buys a plot and later hires Sidra to build on it keeps one profile, one history and one portal login.

### 7.1 Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| CRM-01 | Capture leads from walk-in, phone, website form, Facebook / WhatsApp, and referral; record the source | Must |
| CRM-02 | Assign leads to sales officers; track stage (new, contacted, site visit, quotation, won, lost) and lost reason | Must |
| CRM-03 | Schedule site visits and follow-up calls with reminders to the officer | Should |
| CRM-04 | Customer profile: contacts, KYC documents, all contracts, projects, payments, notes and messages | Must |
| CRM-05 | Duplicate check on phone number and ID number when a customer is created | Must |
| CRM-06 | Customer portal: log in by phone number + one-time code; view contracts, schedule, statement, receipts, project progress and photos | Should |
| CRM-07 | Customer can raise a request or complaint from the portal and see its status | Could |
| CRM-08 | Message templates in English and Somali for SMS, WhatsApp and email; every message sent is logged on the customer | Must |
| CRM-09 | Public listing page of available units that feeds enquiries into CRM | Could |

### 7.2 Notification events

- Reservation made and reservation about to expire
- Contract approved (with schedule attached)
- Payment received (receipt number and new balance)
- Installment reminders and overdue notices (see INS-07)
- Construction stage completed and invoice issued
- Inspection report ready
- Title deed ready for collection

## 8. Reports and dashboards

The General Manager's dashboard answers four questions on one screen: how much was sold, how much was collected, how much is overdue, and which projects are late. Every report filters by date range, scheme, project, officer and branch, and exports to Excel and PDF.

### 8.1 Management dashboard

| Tile / chart | Measure |
| --- | --- |
| Sales this month | Units sold and value, cash vs Murabaha |
| Collections this month | Amount collected vs amount due |
| Collection rate | Collected ÷ due, by month (trend line) |
| Arrears | Overdue amount and number of contracts, by aging bucket |
| Inventory | Units available / reserved / sold per scheme |
| Construction | Active projects, projects behind schedule, invoiced vs contract value |
| Cash position | Balance per cash, bank and mobile-money account |

### 8.2 Standard reports

| Area | Reports |
| --- | --- |
| Sales | Sales register, reservations and expiries, unit availability, price list, commission |
| Installments | Due list (today / this week / this month), collections register, aging, defaulted contracts, early settlements, rescheduled contracts |
| Customers | Customer statement, customer ledger, portfolio by officer |
| Construction | Project status, stage delays, budget vs actual per project, inspection log, retention held |
| Finance | Trial balance, P&L, balance sheet, general ledger, cash book, deferred profit movement, receivables summary |
| Audit | User activity log, cancelled and reversed transactions, discounts and approvals given |

## 9. Data model

The customer sits at the centre: one customer can hold many sale contracts and many construction projects, and every contract or project produces invoices or installments that payments settle and journal entries record. The main tables (MySQL) are below; audit columns (created\_by, updated\_by, timestamps, soft delete) are on every table.

| Table | Key fields | Links to |
| --- | --- | --- |
| customers | code, type (person / company), full name, phone, national ID, address, guarantor | contracts, projects, leads, payments |
| leads | source, stage, assigned\_to, interest (unit / service), lost\_reason | customers, users |
| schemes | name, location, total units, map file | blocks, units |
| units | scheme\_id, block, number, type, size\_m2, cash\_price, status, title\_deed\_no | schemes, reservations, sale\_contracts |
| price\_lists | scheme\_id, unit\_type, price, effective\_from | schemes |
| reservations | unit\_id, customer\_id, deposit, expires\_at, status | units, customers, payments |
| murabaha\_plans | name, min\_down\_%, term\_months, markup\_rate, active | sale\_contracts |
| sale\_contracts | number, unit\_id, customer\_id, sale\_type (cash / murabaha), cash\_price, down\_payment, profit, sale\_price, term, status, approved\_by | units, customers, installments, title\_transfers |
| installments | contract\_id, seq, due\_date, amount, cost\_part, profit\_part, paid\_amount, status | sale\_contracts, payment\_allocations |
| title\_transfers | contract\_id, documents, submitted\_on, deed\_no, handed\_over\_on | sale\_contracts |
| projects | number, customer\_id, service\_type, site, contract\_value, retention\_%, status, manager\_id | customers, project\_stages, boq\_items, inspections, invoices |
| project\_stages | project\_id, name, seq, planned / actual dates, %*complete, billing*% | projects, invoices |
| boq\_items | project\_id, description, unit, qty, rate, amount, actual\_cost | projects, project\_costs |
| inspections | project\_id, date, inspector\_id, checklist, findings, photos, report\_file | projects |
| variation\_orders | project\_id, description, amount, approved\_on | projects |
| invoices | number, customer\_id, project\_id, stage\_id, amount, retention, due\_date, status | customers, projects, payment\_allocations |
| payments | receipt\_no, customer\_id, date, amount, method, reference, cashier\_id | payment\_allocations, journal\_entries |
| payment\_allocations | payment\_id, installment\_id or invoice\_id, amount | payments, installments, invoices |
| accounts | code, name, group, type | journal\_lines |
| journal\_entries / journal\_lines | date, source\_type, source\_id, memo / account\_id, debit, credit | accounts, any source record |
| documents | owner\_type, owner\_id, category, file\_path | any record |
| messages | customer\_id, channel, template, body, sent\_at, status | customers |
| users, roles, permissions | Laravel auth + role-permission tables | all |
| audit\_log | user, action, table, record, old / new values, IP, time | all |

Added in v1.1 from the website and contracts:

| Table / change | Key fields | Links to |
| --- | --- | --- |
| units (new fields) | district, neighbourhood, land\_parcel (Beerta), boundary\_east / north / south / west, plot\_fraction (full / half), offplan\_status, delivery\_date, expansion\_phase | schemes |
| sale\_contract\_units | contract\_id, unit\_id, price | sale\_contracts, units |
| sale\_contracts (new fields) | grace\_months, due\_day, penalty\_rule, default\_rule, title\_deadline\_days, notary\_name, notary\_ref, signed\_on, signed\_copy | contract\_parties, penalties |
| contract\_parties | contract\_id, role (buyer, buyer agent, seller, seller guarantor, witness), name, phone, ID, pledged property | sale\_contracts |
| penalties | contract\_id, type (buyer late / title delay), notice\_served\_on, days, amount, status | sale\_contracts, journal\_entries |
| contract\_clauses | code, title, text\_so, text\_en, default\_on | sale\_contracts |
| brokerage\_listings | owner name / phone, location, size, asking\_price, commission\_%, status | customers, documents |
| verification\_requests | customer\_id, plot details, documents, result, fee, requested\_on, delivered\_on | customers, documents |

Added in v1.3 for configurable terms: **contract\_profiles** (name, is\_default, active, and one column per setting in 5.5), **contract\_profile\_clauses** (profile\_id, clause\_id, on / off), and **sale\_contracts.terms\_snapshot** (a frozen JSON copy of the terms the contract was signed under, plus profile\_id and any approved overrides).

## 10. Non-functional requirements

The system must protect customer identity documents and payment records, keep a full audit trail, and work on ordinary office PCs and phones over slow connections.

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-01 | Security | HTTPS only; passwords hashed (bcrypt); lock account after 5 failed logins; optional two-factor login for staff |
| NFR-02 | Access control | Role-based permissions per screen and action; branch-level data restriction where Sidra has more than one office |
| NFR-03 | Audit | Every create, edit, approve, cancel and login recorded with user, time, IP and old / new values; audit log cannot be edited |
| NFR-04 | Data integrity | Financial records are never deleted, only cancelled or reversed with a reason; database transactions wrap every posting |
| NFR-05 | Backup | Automatic daily database and file backup, kept 30 days, with one copy off the server; restore tested every quarter |
| NFR-06 | Performance | Common screens load within 2 seconds for up to 50 concurrent staff users and 10,000 contracts |
| NFR-07 | Availability | 99% uptime in office hours; planned maintenance outside working hours |
| NFR-08 | Usability | Responsive layout for desktop, tablet and phone; printable A4 contracts, receipts and statements |
| NFR-09 | Language | Interface in English first; contracts, receipts and messages in English and Somali; Somali UI can follow |
| NFR-10 | Currency and dates | USD base currency, two decimals; dates shown DD/MM/YYYY; Africa/Mogadishu time zone (UTC+3) |
| NFR-11 | Documents | Uploads up to 20 MB each (PDF, JPG, PNG, DWG, XLSX); stored outside the public web folder |
| NFR-12 | Maintainability | Code in GitHub with automated tests for pricing, schedules, allocation and postings; every release tagged with its version |

## 11. Technical architecture

SREMS is a single Laravel application on MySQL, served by Nginx on one Linux VPS, with a background queue for messages and a scheduler for reminders and reservation expiry. The staff back office is built with Filament so screens, forms and tables come quickly; the customer portal is a separate, lighter set of pages in the same application.

### 11.1 Stack

| Layer | Choice |
| --- | --- |
| Language / framework | PHP 8.3+, latest stable Laravel |
| Database | MySQL 8 (InnoDB, utf8mb4) |
| Staff back office | Filament admin panel (Livewire + Tailwind) |
| Customer portal | Laravel Blade + Tailwind, phone + one-time-code login |
| Roles and audit | spatie/laravel-permission, spatie/laravel-activitylog |
| PDF and Excel | barryvdh/laravel-dompdf (contracts, receipts, statements), maatwebsite/excel (imports, exports) |
| Backups | spatie/laravel-backup to off-server storage |
| Messaging | Laravel notifications + queue; WhatsApp Business API (chosen); provider adapter so SMS can be added later |
| Server | Ubuntu VPS, Nginx, PHP-FPM, Supervisor for queue workers, cron for the scheduler, Let's Encrypt TLS |
| Source control / CI | GitHub repository, GitHub Actions running tests on every push |

### 11.2 Code organisation

Business rules live in service classes, not in screens, so they can be tested on their own: MurabahaCalculator, ScheduleGenerator, PaymentAllocator, PostingService, StageBillingService.

```
sidra-srems/
├── app/
│   ├── Models/            Customer, Unit, SaleContract, Installment, Project, ...
│   ├── Services/          MurabahaCalculator, ScheduleGenerator, PaymentAllocator, PostingService
│   ├── Filament/          Back-office resources, pages, dashboard widgets
│   ├── Http/Controllers/  Customer portal
│   └── Notifications/     SMS / WhatsApp / email messages
├── database/
│   ├── migrations/
│   └── seeders/           Roles, chart of accounts, posting rules, stage templates
├── resources/views/pdf/   Contract, receipt, statement, invoice templates (EN / SO)
├── tests/                 Feature + unit tests (pricing, schedules, postings)
├── docs/                  This specification, versioned (SREMS-SRS_v1.0.md)
└── .github/workflows/     CI: install, migrate, test
```

### 11.3 GitHub workflow

- Branches: main (released), develop (integration), feature/\<module>-\<item> for each piece of work
- Every merge into main is tagged with a version (v0.1.0, v0.2.0 …) and listed in CHANGELOG.md
- Pull requests must pass the automated tests before merging
- Secrets (.env, gateway keys) are never committed; .env.example documents every setting

## 12. Delivery phases

The build runs in six phases over about 23 weeks, with property sales and Murabaha first because installment collections carry the most money and risk. The weeks are an estimate for a small team (1–2 developers) and will be firmed up once the open questions in section 13 are answered.

&#91;embedded content: delivery roadmap · 6 phases, about 23 weeks\]

Each phase is released to a test server, tagged in GitHub, and signed off by Sidra before the next phase starts; nothing goes live until Phase 5.

## 13. Decisions and open questions

All seventeen questions were answered on 5 Nov 2026; the decisions below are now part of the specification. Where the answer is "varies", the item is a per-contract setting rather than a fixed rule.

| Topic | Decision | Effect on the system |
| --- | --- | --- |
| Installment price vs cash price | Varies by deal | Markup is a per-contract setting (0% or a rate); cash price always recorded beside the contract price |
| Main accounting ledger | Not decided | Build the full ledger (FIN-01 to FIN-07) and the export (FIN-09); Sidra chooses at go-live |
| Payment channels | Cash at office, bank transfer, ZAAD, eDahab | All four set up as receipt methods, each with its own cash / bank / wallet account |
| Offices and users | 1 office, under 10 users | One branch; no branch-level restriction needed in v1 |
| Live installment contracts | 50–200, kept in Excel | Excel import of contracts, schedules and payments to date in Phase 5 |
| Plot / unit list | Unknown if in a spreadsheet | Excel import template provided; manual entry screen as fallback |
| Customer messaging | WhatsApp Business API | WhatsApp is the first channel; adapter kept so SMS can be added later |
| Late penalties | Stay as Sidra income | Default "Penalty goes to" = Penalty income; charity option stays as a setting |
| Early settlement | Discount at GM's discretion | INS-09 as written: optional rebate, GM approval required |
| Construction billing | Varies per contract | Billing schedule (stage % or monthly) set per project contract |
| Retention | Varies per contract | Retention % and period set per project contract, 0 allowed |
| Design and inspection fees | Quoted per job | Fee comes from the job quotation; no fixed price list |
| Hosting | Cloud VPS | Ubuntu VPS as in 11.1 |
| Web address | Decide later | Use a temporary address until Sidra chooses |
| Brokerage commission | Varies per deal | Commission % or fixed amount entered per listing |
| Off-plan house payments | Varies per buyer | Off-plan contracts can use stage-based or monthly schedules, chosen per buyer |
| Logo and letterhead | Use the website logo | Contract, receipt and statement templates use the sidrahomes.co logo |
| Construction stage list (comment, 5 Nov) | Matches | Stage template in 3.1 kept as the default |
| Hagbad full plot payment plan | Use Contract A as the template | Profile A: $11,000 over 14 months, no down payment (see 5.5) |

Still open:

- [ ]
- [ ] Web address for staff and the customer portal
- [ ] Whether SREMS or another package will be the main accounting ledger
