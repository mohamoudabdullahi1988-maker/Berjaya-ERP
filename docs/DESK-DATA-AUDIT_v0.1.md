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

## Decisions only Mohamoud can make

1. **ERPNext Selling for real-estate sales.** Should a Sidra sale also create an ERPNext Quotation or Sales Order? Today the Sidra records are the sale and ERPNext holds only the invoices and payments. Mirroring them would show the sale in Selling, but duplicates the record and its approvals.
2. **ERPNext Assets.** Should Sidra's own assets (vehicles, plant, equipment, office) be tracked in ERPNext Assets? That needs a list or sample of the assets and how depreciation is handled; nothing is invented.
3. **Stores per house** (open in G37): whether each house gets its own ERPNext Warehouse for material usage.

## Applying the Projects fix on the test site

After deploying `develop` (v0.1.69 or later), as root:

```bash
sudo -u frappe -H bash -lc 'cd /home/frappe/sidra/frappe-bench && bench --site sidra.local execute sidra_realestate.pilot_projects.create_pilot_projects'
```

Same guards as the other pilot loaders: Administrator only, the three staging flags, the pilot's manifest must exist, all or nothing, and a rerun changes nothing. It prints the Projects created and any job it skipped (already linked, closed or without stages).
