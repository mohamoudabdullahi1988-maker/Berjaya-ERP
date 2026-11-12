# Staff client API contract v0.1

Current implementation/ownership: [Executive dashboard v0.2](../../../docs/EXECUTIVE-DASHBOARD_v0.2.md), 8 Nov 2026. Codex owns backend and clients end to end. The executive response and native evidence report are implemented; the historical owner/status notes below are superseded. Finance sources remain explicitly unavailable, and gross scheduled dues use their own labelled basis.

7 Nov 2026. Backend owner: Claude. Clients: Codex. Staff only; no customer portal in this version.

## Shared deployment

Host the files in `web/` at **the same HTTPS origin** as Frappe, under `/sidra-staff/`. Browser, Android system WebView and macOS WKWebView load that same page. Session login, MFA, roles, Company User Permissions and business rules remain on Frappe. No API secret is embedded in either app.

Serve an authenticated HTML page that sets `window.SIDRA_CONFIG` before loading `app.js`, including `csrfToken: frappe.session`'s actual request CSRF token (use Frappe's normal request-context API; do not hard-code it). The static `config.js` preserves an injected config. Do not cache authenticated HTML/API data; use `Cache-Control: private, no-store`. Send a CSP allowing the same-origin UI plus Google Maps frames only if embedding is enabled. The optional Google Maps Embed browser key must be restricted by HTTP referrer and API; it is not a server secret. Links and KML work without it.

The app's Sign in action uses `/login?redirect-to=%2Fsidra-staff%2F`. Sign out posts `/api/method/logout` with the session CSRF token. Verify both against the configured SSO/session policy on the real server. Federated SSO that requires an external system browser needs a separate tested authentication flow; it is not claimed here.

## Dashboard

`GET /api/method/sidra_realestate.api.staff_dashboard.get_dashboard?company=<permitted id>&period=this_month`

Periods: `this_month`, `last_30_days`, `last_90_days`. Compute the period on the server in Africa/Mogadishu. The first request may omit company; choose a permitted company. Return only companies and records that this staff user may read. Never use unrestricted `get_all` or client-side filtering as the security boundary. Snapshot response: Frappe `{"message": payload}`.

The exact example is `web/demo.js` (fictional). Required payload:

- `schema_version: 1`, `as_of` ISO timestamp with offset, `scope: {company_id, company_name, role_label}`, `companies: [{id,name}]`, `currency` ISO code.
- `summary: {new_leads, units_available, active_reservations, confirmed_contracts, agreed_contract_value}`.
- `property: {total, counts:[{status,count}]}`. Statuses come from the server.
- `schedule: {buckets:[{label,amount}], upcoming:[{contract_id,external_reference,customer_display,due_date,amount,currency,row_type}]}` Optional `available`/`reason` (false when the role cannot read sale contracts). Buckets are `Due today`, `Next 30 days` (tomorrow through day 30, the same window as the executive `due_next_30_days`), `31-60 days`, `61-90 days`; a bucket amount is null when a row in it has no valid amount.
- Record types the user's role cannot read give null summary counts/values, `property.total: null`, empty lists and `schedule.available: false`, never a page error, so construction-only roles still get their jobs view.
- `contracts:[{id,reference,customer_display,unit_label,status,value,currency,signed_on}]`.
- `locations:[{doctype,name,label,area,status,latitude,longitude,modified,can_write}]`. Allowed types: Sidra Unit, Sidra Construction Job. Coordinates may both be null. Include only permission-filtered results. `modified` is the parent record timestamp; `can_write` is a server permission result. The UI refreshes an individual location with `get_location` before editing.
- `sales: {available, reason?, qualified_opportunities, conversion_rate, pipeline:[{label,value}]}`.
- `payments: {available, reason?, received, overdue, collection_rate, overdue_contracts, aging:[{label,amount}]}`.
  - Opt-in persisted financial demo only (`docs/FINANCE-DEMO_v0.2.md`): `basis: "native_invoice_demo"`, `overdue_invoices`, `overdue_contracts: null`, and a fictional-data notice. Receipts and invoice balances come from permitted native submitted vouchers in the finance demo Company (Sidra Homes on the test site, decision G13). Collection rate is settled invoice value / due-through-today invoice value; overdue means due before today. Production-company payments remain unavailable. Do not label these invoice balances as contract arrears.
- `jobs: {available, reason?, active, overdue_milestones, awaiting_inspection, completed, items:[{id,label,status,progress,next_milestone,due_date}]}`. `overdue_milestones` counts stages of Contracted/In Progress/On Hold jobs that are past their planned end with no actual end and completion below 100 (shared rule `stage_overdue`, also used by the executive stage exceptions).

Unavailable groups must use `available:false` and a clear `reason`. Missing accounting integration is not zero receipts or zero arrears. Monetary JSON values should be decimal strings. Do not sum different currencies without Finance-approved conversion; return one company/currency scope.

`summary.new_leads` is independent of `sales.available`: the server may supply a readable creation count while qualification stages remain undefined. A known zero is valid; null means unavailable. Individual job counts, rates and monetary values may also be null/missing; the client must not convert them or blank strings into a zero. The current operational job endpoint returns current company records, not period-filtered historical counts. Implementation status and pending executive/HTTPS integration are recorded in [dashboard handover v0.2](DASHBOARD-HANDOVER_v0.2.md).

### KPI definitions for backend agreement

- New leads: ERPNext Lead creation in the selected period. Qualification and conversion must use documented, linked server stages/cohorts; an externally registered contract is not automatically a converted lead.
- Confirmed contracts / agreed value: commercial Sidra contracts, distinct from recognized revenue.
- Payments received: posted, uncancelled native ERPNext receipts linked to contracts; refunds and reversals follow Finance's agreed net/gross definition. No custom payment ledger.
- Collection rate: amounts settled against a defined due cohort divided by that cohort's amount due. Do not mix unrelated advance receipts with the denominator.
- Overdue: unpaid due obligations after authoritative payment allocation and permitted adjustments; age in 1–30, 31–60, 61–90, 90+ day buckets. The schedule alone cannot establish unpaid balances.
- Construction: existing jobs, milestones and inspection records only. Return unavailable where the actual workflow/data does not exist. No invented completion %, certifications, costs or margins. Margin KPIs wait for reliable actual costs and commitments.

## Executive overview extension

See [Executive dashboard API v0.1](EXECUTIVE-API_v0.1.md) and its [implemented v0.2 update](../../../docs/EXECUTIVE-DASHBOARD_v0.2.md) for the executive response and native report. The gross-schedule basis is explicitly labelled before settlements; project associations and HTTPS/device acceptance remain pending. No further Claude handoff is required.

## Plot and site location API

PR #28 integrates this API into `sidra_realestate/api/locations.py` and `location_geometry.py` with native DocType Geolocation fields named `sidra_location`. Deploy through the normal app migrate/build process. The older isolated source under `clients/staff/integration/` is retained for reference and stubbed tests; do not copy it over the integrated backend or install duplicate Custom Fields. Existing site `gps` text is read conservatively and preserved. A location pin is not a parcel survey or legal boundary.

Preserve native fields, GPS text and other geometry. No extra app or historical adapter field-installation command is needed for the integrated implementation.

- GET `...locations.get_location?doctype=Sidra%20Unit&name=<id>`: validates allowed parent type and parent read/Company permissions. Returns latitude/longitude, source, configured, unsupported_geometry, modified, can_write and Google Maps/Earth links.
- POST `...locations.set_location`: `{doctype,name,latitude,longitude,expected_modified}`. Session + CSRF, parent write and Company permissions, draft/non-submitted parent only, finite/ranged coordinates, optimistic timestamp check under row lock. Only the validated pin column changes; no reservation, pricing, BOQ, contract or accounting calculations run. Parent modification/audit comment/realtime notification are updated. No client can bypass parent permissions by choosing another doctype.
- GET `...locations.export_kml?doctype=...&name=...`: authenticated parent read check, downloads a correctly escaped WGS84 Point KML for Google Earth. No parcel boundary is invented.

Google Maps URL API and Earth search links require no paid API key. This implementation does not call Google geocoding, promise a satellite/basemap without configuration, or turn a position into legal/survey evidence. Live Google links and device geolocation still require platform/server testing.

## Backend integration tests still required

Run with actual Sidra roles and Company restrictions: denied read/write, cross-company denial, stale edits, concurrent edits, submitted parent refusal, GPS preservation, unsupported polygon preservation, saved/reopened coordinate order, KML private access, CSRF/expired session, no changes to unit status/prices/BOQ/contracts/financial documents. Current adapter tests isolate the Python boundary with a stub; they are not Frappe integration results.

### Recorded sales activity (12 Nov 2026)

Sales now returns `basis: "recorded_lead_status"` with counts of readable Lead records created in the selected Company and period, grouped by their actual status. Qualification and conversion remain null; a status named Converted does not establish a contract-to-lead link. No readable leads is an available empty cohort; denied Lead access is unavailable. No role changes or posting rules are introduced.
