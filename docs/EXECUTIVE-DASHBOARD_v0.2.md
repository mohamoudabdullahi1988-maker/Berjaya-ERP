# Executive dashboard implementation v0.2

8 Nov 2026. Codex owns this dashboard implementation and tests end to end under Mohamoud's latest instruction. Supersedes the earlier requirement to defer backend work to Claude. SRS §3.6 and the existing Finance/legal gates remain in force.

## Reuse and scope

Extends the existing staff endpoint/page and client from PRs #26/#28/#29. Reuses the source definitions reviewed and natively tested in the merged Insights package: signed contract value, consistent unit/scheme Company linkage, separate parent/unit/schedule cohorts (no join multiplication), gross dues tomorrow through day 30, and recorded stage date exceptions. No extra app, accounting ledger, receipt import, financial posting, approval or construction workflow is installed. The BI package remains independent; Desk permissions are not assumed to authorize Insights.

## Server behavior

`get_dashboard` keeps schema version 1 and adds `executive`. Only existing Sidra General Manager/System Manager roles receive management data; ordinary staff receive an unavailable executive group. This is read authority only, not business approval. Every parent query uses `frappe.get_list` and current role/Company/Unit permissions. Child queries are constrained by readable, consistent parents, parenttype and parentfield. A contract with any inaccessible/missing/inconsistent unit/scheme or inconsistent allocation is excluded in full, never partially counted. Sales details disclose the readable exclusion count and the permitted-cohort basis.

All dates are resolved in Africa/Mogadishu. Sales use signing date between period start and today inclusive, submitted status and Company currency; last-30/90-day windows contain exactly 30/90 days including today. Six-month trends use the same eligible sales cohort and identify the partial current month. Cash history is null, never zero, when unintegrated. Current inventory, cancellations and recorded exceptions are not historical period snapshots.

Three headline sources are available now: signed commercial value (not revenue), available-unit count with asking value only when all prices are positive/known, and **gross scheduled** next-30-day obligations. `due_next_30_days.basis="gross_schedule"` changes the client label to **Scheduled next 30 days**, explicitly before settlements and not expected cash. Same-day rows retain their identities; fees/down payments with schedule dates are counted as recorded. Separately recorded undated down-payment obligations are excluded. This is an additive clarification of the original proposed unpaid-dues field, not a claim that payment allocation exists.

Cash collected, unpaid arrears, targets, forecast collections, inspection counts and approved-baseline on-schedule performance are not invented. Source data/policy does not yet establish them. Recorded stage exceptions are exposed separately (past planned end and incomplete, or actual end after planned end), including real engineer/date/source links where present. Reservations past recorded expiry prompt review, never automatic release. Registration age is median days since registration of currently available units, not days in Available status. Unknown source coverage is labelled partial/unavailable; it cannot become a zero-escalation claim. The decision list shows at most ten recorded exceptions, sorted by recorded date, with the full count and supporting reports.

## Supporting report and deployment

**Sidra Executive Detail** is a standard native Script Report under Sidra Sales. Normal app `migrate` installs the Report metadata; normal `build` publishes the shared staff assets. No customer/business schema migration or record rewrite is added. Install/update through the existing deployment process; do not reinstall the historical location adapter. Staff uses `/sidra-staff/` on the site's HTTPS origin.

Report filters: permitted `company`, `period`, one supported source `metric`, optional current Mogadishu `as_of` date. Non-permitted Company, unsupported project associations, invalid metric/period or a stale dashboard date are refused. The report rechecks authorization on direct access/export and re-reads live records; it is not a stored historical snapshot and may change after the dashboard refresh. Source record IDs and schedule/stage IDs are retained for reconciliation. Native report links contain only company/period/date/cohort filters and use existing record navigation.

Project selection stays disabled until a consistent property/contract/construction association is approved; a supplied project is rejected rather than ignored. No new project relation is guessed.

## Verification and remaining limits

Pure tests cover exact decimals, inclusive windows, leap/year boundaries and recorded stage semantics. Frappe integration tests persist synthetic contracts/units/stages and reconcile the snapshot to the actual native report, including multi-unit/same-day schedule fan-out, missing sources, Company/Unit restrictions, management/direct-report denial, date/currency/source-link exclusions and no financial/source modification. Client/browser tests cover gross schedule labelling and partial decision coverage alongside the existing dashboard/location checks. See the implementation PR for final CI results; fixtures are not production acceptance.

The coding environment has no connected VPS identity/HTTPS URL or usable local v16 Python interpreter. CI provides the actual pinned Frappe/ERPNext/MariaDB installation and tests; no live deployment or Android/macOS physical-device acceptance is claimed. HTTPS/CSP/session/device checks remain necessary when access is available. Reading operational values does not approve financial posting or solve the missing receipt-allocation/target/baseline sources.
