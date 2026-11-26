# Berjaya ERP delivery decision and handover v0.3

24 Nov 2026 · Decision by Mohamoud Abdullahi Sheikh for `Berjaya-ERP/develop`.
See also [G43 in v0.4](DECISIONS-AND-GATES_v0.4.md) (first numbered G38) for the approved contract-to-invoice reporting and allocation policy.

## G36 · Berjaya dashboard and ERPNext Desk

For this delivery, staff use **Berjaya at `/berjaya` for reports and their most frequent transactions**. They use **ERPNext Desk for the rest of their work**, with normal Frappe permissions. Berjaya can stay the landing page and link directly to the Desk workspaces and records staff need. Remove the custom Desk-to-Berjaya restriction for authorized staff so those links work. Preserve existing Berjaya record URLs and underlying business records during the transition.

This supersedes the full interface replacement in G17 and G23, the Desk restriction in G24, and G25's sample-first landing page for the delivery. The grouped navigation from [PR #4](https://github.com/mohamoudabdullahi1988-maker/Berjaya-ERP/pull/4) and the existing [Cashbook & Reconciliation](https://github.com/mohamoudabdullahi1988-maker/Berjaya-ERP/pull/3) are the starting point. [v0.2](DECISIONS-AND-GATES_v0.2.md) remains in force for business rules, financial gates, and earlier decisions outside this scope.

## G37 · Construction uses ERPNext Projects

Use native ERPNext **Project** and **Task** as the foundation for managing construction jobs and stages. Use one Project per house or job as the initial mapping. Evaluate and preserve existing Sidra Construction Job records, signed terms, BOQs, variations and inspections. Where an existing record must remain in use, link it to the appropriate Project and reuse its approvals. Document the mapping and adoption path before converting any live records.

Siham reported that stage certification leads Finance to update project cost reporting and check whether a customer or contractor payment is due. Finance looks at the site supervisor's report and the signed agreement's dates or milestones before processing a stage-dependent payment. Keep that review distinct from stage certification and preserve G11 and current posting gates. Siham described general bookkeeping, separate stores per house, irregular reporting of material usage, and no standard process for tracking investor funds. Standard stage labels and investor-fund treatment remain open.

## G38 · General Manager approval for identity access (25 Nov 2026)

Mohamoud, implementing G32. A **Sidra KYC Access Request** records the approval for one staff member and one buyer's identity record. A Sidra Sales Manager or the General Manager raises it with a reason; only the General Manager approves, refuses (with a reason) or revokes it. On approval the GM sets the last day of access (30 days by default); the person can then read that one record and download its identity documents, which G32 counts as the same approval. They cannot edit or re-share it. Access ends when revoked or, automatically, after its last day. Every other share of a KYC record stays refused, in Desk and in Berjaya. Role permissions on the KYC record are unchanged. The request screens are in Desk; Berjaya can call the same server methods (`approve`, `refuse`, `revoke` in `sidra_kyc_access_request.py`).

## G40 · Sidra sales also appear in ERPNext Selling (25 Nov 2026)

Mohamoud, answering the Desk data audit. An issued Sidra Sale Quotation creates a submitted ERPNext **Quotation**; a confirmed Sidra Sale Contract creates a submitted ERPNext **Sales Order**. Each copy has one line per unit with a sale-type item (*Land plot sale*, *House sale*, *Apartment sale*; the unit is on the line) and links back to its Sidra record. The Sidra records stay the sale and keep their approvals; the copies are records only and follow them (cancelled with them, never by hand). Prices are copied, not worked out. No invoice, payment or ledger entry is created by this; invoices and payments keep the existing finance flow and gates.

## G41 · Sidra's own assets in ERPNext Assets (25 Nov 2026)

Mohamoud. Sidra's own assets (vehicles, plant and equipment, office equipment, IT equipment) are tracked in ERPNext Assets with **straight-line** depreciation at proposed useful lives: vehicles 5 years, plant and equipment 8, office equipment 5, IT equipment 3. Finance approves the method, lives and accounts **before any depreciation entry is posted**; until then automatic depreciation posting stays off. Plots and houses for sale remain Sidra Units, not assets.

## G42 · A store per house (25 Nov 2026)

Mohamoud, resolving the stores question of G37. Each construction job (house) gets its own ERPNext **Warehouse**, created with its Project, under a *Construction sites* group. Material requests per house can be raised now. Stock moves that post to the ledger (receipts, transfers and issues into a house store) wait until Finance approves the stock accounts, as the finance posting gate requires.

## Sidra feedback and first dashboard scope

Siham selected these three reports in her Finance, Site Inventory and Project Reporting response (21 Nov 2026, Q13):

1. Customer statement by contract.
2. Overdue installments.
3. Supplier balances and payments.

Use existing permitted contract, installment, purchasing and ERPNext accounting records for the report figures. Verify that the statement and overdue report keep each contract's balance distinct even when one customer has multiple agreements.

The transaction shortlist below is inferred from the respondents' recent workflows. It is the starting scope for implementation.

| Berjaya shortcut | Feedback and implementation boundary |
| --- | --- |
| Find an agreement and record a payment | Salman searches by customer name or phone for plot and construction payments. Siham identifies the correct balance by plot, project or house number. Use the customer-specified installment for partial payments where the approved workflow supports it. Issue the receipt after Finance confirms the payment. Keep the existing financial controls and use ERPNext for any step outside approved Berjaya actions. |
| Cashbook & Reconciliation | Reuse the merged Finance screen. Siham reconciles bank receipts individually against evidence and batches ZAAD and eDahab by payment method. An assigned approver handles corrections or reversals based on amount or type. Real provider-column mapping still needs anonymized statements ([issue #1](https://github.com/mohamoudabdullahi1988-maker/Berjaya-ERP/issues/1)). |
| Plot reservation and quotation | Salman's recent sale went from reservation to quotation. Provide shortcuts into the existing workflow. Preserve G35's Finance-verified down payment before a plot hold and retain the approved confirmation rules. Salman described Sales preparing the signed agreement and Eng. Mohamed confirming it. Verify how that maps to the configured approval role before changing permissions. |

Salman also requested the first installment reminder by WhatsApp on the due date. Track it as a follow-up to the immediate dashboard delivery. Sources are the completed `fin-siham.pdf` and `sales-eng.saleban.pdf` supplied on 24 Nov 2026. Use fictional fixtures in Git.

## Implementation split

Start from the latest `develop` after this handover merges. Each owner uses a separate branch and PR into `develop`.

| Owner | Branch | Implementation and acceptance |
| --- | --- | --- |
| Claude Code | `feature/construction-erpnext-projects` | Own the ERPNext Desk access change and Construction integration in `sidra_realestate/`. Verify a normal authorized staff user can open the intended Desk pages directly and from Berjaya. Verify restricted records stay restricted. Map a fictional house/job to an ERPNext Project and Tasks, verify the job can be traced from the existing construction records and the finance review can use the signed milestone and supervisor evidence. Share the verified Desk routes and data mapping in the PR. |
| Codex | `feature/berjaya-delivery-dashboard` | Own the Berjaya frontend, read-only reporting queries or adapters, and the three shortcuts listed above. Validate the report totals against source records and test company/role access. Verify two agreements for the same fictional customer keep separate balances. Reuse the existing Cashbook route and wire Desk links using Claude's verified routes. Verify the links and key flows on desktop and mobile. |

Claude can begin Desk access and the Project/Task mapping while Codex builds and tests the reports and existing shortcuts. The Desk routes and project identifier are the integration points. Claude owns the Desk redirect and construction data changes. Codex owns Berjaya navigation and report presentation. Review the end-to-end flows together after both PRs land.
