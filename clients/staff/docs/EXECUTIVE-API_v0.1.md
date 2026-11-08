# Executive dashboard API v0.1

Implementation update, 8 Nov 2026: Codex now owns this work end to end. [Executive implementation v0.2](../../../docs/EXECUTIVE-DASHBOARD_v0.2.md) supersedes the implementation status and adds explicit `basis:"gross_schedule"` support plus partial exception coverage. The original unavailable Finance/target/baseline constraints below remain in force.

7 Nov 2026. Backend/test server: Claude. Shared web and Android/macOS clients: Codex. Integration proposal for the existing dashboard endpoint; no backend implementation or approved accounting-policy change is supplied here.

## Request and scope

Extend `GET /api/method/sidra_realestate.api.staff_dashboard.get_dashboard` from [API-CONTRACT.md](API-CONTRACT.md). Keep `schema_version:1` and the existing operational payload. Add the optional `executive` object described below. Older payloads render all six executive cards as unavailable; the client never reconstructs them from `summary`, schedules or contracts.

Parameters: `company` (optional on first load), `project` (optional, omitted for all permitted projects), and `period` (`this_month`, `last_30_days`, `last_90_days`). Resolve dates in Africa/Mogadishu. Return `scope.company_id`, `scope.company_name`, `scope.project_id` (null for all), and `scope.role_label`; `companies:[{id,name}]` and `projects:[{id,name}]` contain only permitted choices for the selected company. Company changes clear the project before requesting a fresh snapshot. The server must reject unauthorized companies/projects and unsupported project associations; do not silently treat them as unrestricted queries. Define the relationship between property schemes, contracts and ERPNext Projects on the server before enabling a project choice. A project scope must apply consistently to every section or explicitly mark unsupported sections unavailable.

Authorize the staff session and management reporting capability on the server. A role label is display text, never permission evidence. Use existing roles and Company User Permissions; do not add a CEO/GM authorization bypass. Deny the whole request with 401/403 where appropriate, or omit executive data/use `{available:false,reason:"Management access required"}` when operational data remains readable. Do not send restricted executive values to a user who lacks permission. Apply parent/record/report permissions on each drilldown too.

## Executive payload

Return `executive:{available:true,period_label,freshness,metrics,trends,decisions,exposure}` inside the Frappe `message` envelope. All totals, target attainment, statuses, age/schedule cohorts, decisions, impacts and permissions are supplied by the server. Decimal monetary strings preserve source precision. The client only formats numbers and scales chart bars. Return one company/currency scope; no client FX conversion. Null/missing/unusable values are not zero. Each group or metric can instead be `{available:false,reason}`. A real zero uses `{available:true,value:"0"}`.

`freshness:{status:"fresh"|"stale"|"unknown",label}` describes source completeness and age, not the time a browser refreshed. Top-level `as_of` is an ISO timestamp with timezone. Include dates, the relevant stale/missing source and any lag in the label; the client does not invent a freshness threshold. If any required source is unavailable, do not present its dependent metric as current or complete.

`metrics` is keyed by the following six IDs. Common fields: `available`, `value`, `detail`, optional `status` (`on_track`, `attention`, `critical`), `status_label`, `reason`, `drilldown`.

| ID | Value and additional fields | Server source / definition boundary |
| --- | --- | --- |
| `sales_value` | Agreed commercial sales value; optional `target`, `attainment_percent` | Eligible confirmed Sidra Sale Contracts in the selected period; define/expose the date/status basis. Target must be approved for the same scope, currency and period. Never label sales value as recognized revenue. |
| `cash_collected` | Posted receipts; optional `target`, `attainment_percent` | Native ERPNext Payment Entry and authoritative allocation. Finance must define gross/net treatment of refunds/reversals and project attribution. Schedule rows and captured down-payment obligations are not receipts. |
| `overdue_balance` | Unpaid overdue contractual obligations as of snapshot | Requires authoritative settlements, allocations and permitted adjustments. Return unavailable until these exist. Explain the arrears date/cohort basis in detail/report. This is not automatically posted accounting AR. |
| `due_next_30_days` | Unpaid contractual dues in the upcoming 30-day window | Supply exact window dates in `detail` (preview uses 8 Nov–7 Dec inclusive). Optional `expected_receipts:{available,value?,reason?}` is a separate approved forecast; omit/mark unavailable until one exists. Do not equate contractual dues with expected cash. |
| `projects_on_schedule` | Number of eligible active jobs on schedule | Existing Sidra Construction Job / linked ERPNext Project, approved baseline and milestone evidence. Supply the denominator and exceptions in `detail`/`status_label`. No invented progress, schedule baseline, inspection or cost. |
| `available_units` | Available-unit count; optional `asking_value` | Permission-filtered Sidra Units and effective asking prices. Asking value is not asset cost, margin or revenue. Unknown/incomplete pricing means asking value unavailable. |

Targets can be null/unset while actuals are available. Only include `attainment_percent` as a finite JSON number when the matching target/denominator is meaningful. The server owns thresholds and period comparisons; the browser does not divide actuals by targets.

`trends:{available,period_label,months:[{label,sales_value,received}],reason?}` supplies ordered monthly aggregates with the same definitions as sales/collections. Identify a partial current month in the label/range. A missing series value renders as a dash, including in the exact-value table; a verified zero renders as zero. Do not replace missing historical integration with zero. Define the trend horizon and selected-period relationship on the server.

`decisions:{available,total,items,reason?}`: each item is `{id,reference,title,priority,priority_label,impact:{amount?,currency?,description},owner,due_date,next_action,drilldown}`. Dates are ISO `YYYY-MM-DD`; owner, deadline and next action may be absent and render as unassigned/unset. Priorities use the status enum above. `total` counts open cases in the same scope; document any result limit in the payload text. Return only existing permission-filtered cases, never simulated approvals or automatic cancellation/release actions. Impact may be narrative when not quantifiable. Do not guess amounts or sum overlapping risks. Supporting reports must identify the case and its actual source records.

`exposure:{available,items,reason?}`: each item is `{label,available,value,kind:"money"|"count",detail,reason?,drilldown}`. The preview illustrates cancelled contracts, reservations past follow-up, available inventory age and a management-review subset of overdue accounts. Supply the actual cohort/age basis in `detail` and supporting report. Management-review accounts are a subset, not the full aging balance. This is read-only reporting, with no new cancellation, release, posting, penalty, refund or title-transfer behavior.

## Supporting records

`drilldown:{path}` is a server-created same-origin `/app/` URL pointing to a native record/list or query report. Accepted routes are `query-report/<report>` and `sidra-sale-contract`, `sidra-unit`, `sidra-construction-job`, `sidra-reservation`, `payment-entry`, `lead`, `opportunity` (optionally a record ID). Other routes are rendered without a link. URL-encode names and query values. Include the exact company/project/period/as-of/status/cohort filters needed to reconcile the displayed figure. The browser retains these filters; the destination must independently enforce permissions. A filtered list is not a substitute for report authorization. Do not supply a link until the report exists.

`drilldown.preview:{columns,rows}` exists only in the explicitly requested `?demo=1` fixture. Live mode ignores it. Fictional reports are not installed ERPNext reports. Preview filters are disabled because its snapshot is fixed; supporting cohorts reconcile to the displayed fixture totals. Small operational registers in the preview are illustrative extracts, not full executive cohorts.

## Required integration evidence from Claude

- Allowed/denied staff and management accounts; Company/project membership and cross-company rejection, including direct report URLs and source documents.
- Reconcile each available card and month to persisted records with identical scope and snapshot basis. Exercise zero, partial and advance receipts, allocations, cancelled/reversed vouchers and missing Finance integration using approved Finance rules.
- Approved target source, missing target, zero target, partial periods, currency isolation, overdue cutoffs, exact next-30-day boundaries and Africa/Mogadishu month changes.
- Existing job baselines/milestones, missing schedule data, unavailable costs/asking prices, decision ownership/deadlines and overlapping exposure subsets.
- Fresh/stale/unknown source states; expired sessions, CSRF, no-store authenticated responses and actual report installation.
- Serve `/sidra-staff/` at the forthcoming HTTPS origin, inject CSRF, and test browser/Android/macOS sessions, navigation and protected downloads on actual devices.

Local automated browser tests use an in-browser API fixture to verify UI behavior and outbound filters. They do not prove any of the above Frappe integrations or permission enforcement.
