# Desk data audit v0.1

25 Nov 2026 · Recorded by Claude Code for Mohamoud. What the fictional pilot loaders populate for Company **Sidra Homes**, and which ERPNext Desk modules have no source records in that dataset. Confirm the deployed version, Company and user permissions on the test site with the read-only audit.

Counts on a site, read only: `bench --site sidra.local execute sidra_realestate.desk_audit.count_records --kwargs "{'company': 'Sidra Homes'}"`.

## Module by module

| Desk module | Expected from the pilot loaders | Why | Where the data is | Action |
| --- | --- | --- | --- | --- |
| **Projects** (Project, Task) | Empty | Construction jobs got an ERPNext Project only when someone pressed **Create → Project** (v0.1.65). The pilot loader created 25 jobs but no Projects. | Sidra Construction Job | **Fixed here:** `pilot_projects.create_pilot_projects` gives every pilot job its Project and one Task per stage. Live jobs: Create → Project per job (`docs/CONSTRUCTION-PROJECTS_v0.1.md`). |
| **Selling** (Quotation, Sales Order, Delivery Note) | Empty | Real-estate sales are Sidra records, by design since the SRS: they carry units, contract profiles, schedules and title rules ERPNext's Selling records do not. Nothing creates an ERPNext Quotation or Sales Order. | Sidra Sale Quotation, Sidra Reservation, Sidra Sale Contract, Sidra Title Transfer (module *Sidra Sales*) | **Decision for Mohamoud** (below). |
| **Assets** (Asset) | Empty | No loader or screen creates an ERPNext Asset. "Asset" in the demo loaders is only an account type (Bank, Receivables). Plots and houses for sale are Sidra Units, not company assets. | — | **Decision for Mohamoud** (below). |
| **Accounting** (Sales/Purchase Invoice, Payment Entry, Journal Entry) | Has data | The finance demo (G14) and pilot (G16) post about 160 fictional vouchers through the guarded loaders. | ERPNext | None. |
| **CRM** (Lead, Opportunity, Customer) | Has data | Pilot buyers are Customers; the pilot top-up adds Leads and Opportunities. | ERPNext + Sidra Customer KYC | None. |
| **Buying** (Supplier) | Suppliers only | Demo purchases are Purchase Invoices; no Purchase Order or Receipt is created. | ERPNext | Follows the open stores / material-usage question (G37). |
| **Stock** (Item) | Items only | Demo Items are service items for invoices; no Warehouse stock moves. Separate stores per house are an open question (G37). | ERPNext | Follows that decision. |
| **Construction** (Sidra) | Has data | 25 jobs, quotations, variations, inspections, risks from the pilot loaders. | Sidra Construction | None. |

## Decisions (Mohamoud, 25 Nov 2026)

1. **ERPNext Selling for real-estate sales: yes** (G40). Issued Sidra quotations create ERPNext Quotations and confirmed contracts create Sales Orders, as records only. Built in v0.1.71; existing sales are copied with `services.erpnext_selling.backfill_selling`.
2. **ERPNext Assets: yes** (G41). Straight-line at proposed lives; no depreciation entry until Finance approves.
3. **Stores per house: yes** (G42). One Warehouse per house with its Project; ledger-posting stock moves wait for Finance's stock accounts.

## Applying the Projects fix on the test site

After deploying `develop` (v0.1.69 or later), as root:

```bash
sudo -u frappe -H bash -lc 'cd /home/frappe/sidra/frappe-bench && bench --site sidra.local execute sidra_realestate.pilot_projects.create_pilot_projects'
```

Same guards as the other pilot loaders: Administrator only, the three staging flags, the pilot's manifest must exist, all or nothing, and a rerun changes nothing. It prints the Projects created and any job it skipped (already linked, closed or without stages).

## Role visibility in Desk (26 Nov 2026)

Data in a Desk module is only useful if staff may open it. From the role profiles (`install.py`) and ERPNext v16's own permissions, read is what each Sidra profile gets today (*select* = can pick it in a link field, cannot open it):

| Record | Sales Staff | Sales Management | General Management | Project Staff | Inspection | Finance Review |
| --- | --- | --- | --- | --- | --- | --- |
| Quotation | read, write | read, write | read, write | – | – | – |
| Sales Order | read, write | read, write | read, write | select | select | – |
| Item | read | read | read | – | – | – |
| Project | select | select | select | read, write | read, write | – |
| Task | – | – | – | read, write | read, write | – |
| Asset, Asset Category | – | – | – | – | – | – |
| Warehouse | read | read | read | – | – | – |
| Material Request | – | – | – | – | – | – |

On a site, people may hold more roles than their profile. Check the real users, read only:

```bash
sudo -u frappe -H bash -lc 'cd /home/frappe/sidra/frappe-bench && bench --site sidra.local execute sidra_realestate.desk_audit.role_visibility'
```

### Gaps

1. **Finance Review sees none of it**: no Sales Orders, Projects, Tasks or Assets.
2. **Nobody can open Assets.** ERPNext gives Assets only to *Accounts User* and *Quality Manager*; no Sidra profile has either.
3. **General Management cannot open Projects or Tasks.**
4. **Project Staff cannot raise a Material Request** for a house store, or open the store (Warehouse) or the Items, though G42 lets Material Requests be raised now.
5. **Sales roles can write ERPNext Quotations and Sales Orders.** ERPNext's *Sales User* role allows staff to make their own besides the copies of Sidra records (G40).

### Decided (G44, 26 Nov 2026)

Gaps 1, 2, 4 and 5 are closed by G44 (`services/desk_permissions.py`, applied on migrate): Finance reads Sales, Projects, Tasks and Assets; General Management and Project Staff read Assets; Project Staff raise Material Requests and read Warehouses and Items; hand-made ERPNext Quotations and Sales Orders are refused. Gap 3 is closed by G45 (28 Nov 2026, v0.1.76): General Management reads Projects and Tasks, without create or edit.
