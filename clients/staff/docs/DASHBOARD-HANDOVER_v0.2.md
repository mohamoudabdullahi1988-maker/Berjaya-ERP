# Staff dashboard handover v0.2

8 Nov 2026. Backend/test server: Claude. Staff web, Android and macOS clients: Codex. Continues the CEO/GM dashboard request; supersedes older implementation-status statements in `CLAUDE-HANDOVER.md`, not its business constraints.

## Existing implementation reused

- PR #26 completed the six executive cards, monthly trends, decision owner/deadline/action, exposure, supporting records and browser coverage. No second executive UI was built.
- PR #28 added the actual Frappe operational dashboard, `/sidra-staff/` page with session CSRF injection, and plot/site location APIs/native Geolocation fields. This continuation is based on develop `50294fe`.
- Insights PR #27 remains a separate draft. Its workbook/source assessment was inspected; no Insights install, integration, merge or deployment was performed. Reuse its reviewed reporting definitions where appropriate after backend/permission review; do not copy unrestricted SQL into the client or presume BI permissions equal Desk permissions.

## This continuation

Branch: `feature/staff-dashboard-data-states`. Client web version: 0.1.1. No native-shell, backend, schema, financial-policy or record changes.

- Show a server-supplied new-lead count independently of qualification/pipeline availability. A known zero remains zero; a null count is unavailable. No count is inferred from contracts.
- Render absent job/inspection counts, payment amounts, overdue-contract counts and conversion/collection rates as unavailable. Do not show a blank card, `undefined%`, or coerce an empty monetary string into a zero balance.
- Label the current operational job counts as current company records rather than asserting that the period selector filtered them; the existing backend returns a current snapshot.
- Preserve the existing executive, map, schedule and department screens. No receipts, arrears, decisions or targets are calculated in the browser.

## Verification and practical limits

Local commands: `npm test`, `npm run check`, `python -m unittest discover -s tests -p 'test_*.py'`, and `node tools/browser-smoke.mjs` with Node 24/Chromium. Node source contains 17 named checks. Existing Python tests are 12 stubbed geometry/API-boundary tests, not live Frappe acceptance. Browser checks include six-card evidence, scope/filter requests, stale/restricted/missing data, out-of-order replies, 320/390px layouts, map links and invalid coordinates, plus independent lead counts and partial operational KPI values.

The new browser cases use explicit in-browser API fixtures matching the new endpoint's nullable fields. They verify display/request behavior; they do not establish server permissions, financial reconciliation, actual staff records or device GPS behavior. Check the feature PR for final CI and native packaging results; local Linux has no Android/macOS build toolchains. Local browser/server execution required permission to open local ports outside the command sandbox.

## Remaining work and Claude's next review task

1. Implement the optional executive response described in [EXECUTIVE-API_v0.1.md](EXECUTIVE-API_v0.1.md) using existing permission-filtered sources. The current endpoint omits it, so six executive cards deliberately remain unavailable on that payload. Review exact date/status/currency cohorts, complete filtered supporting reports, approved target source and freshness evidence before declaring those metrics available.
2. Keep actual cash collected, unpaid overdue amounts and collection/conversion rates unavailable until their source mappings, allocations and definitions exist. A schedule or captured down payment obligation is not cash received; gross scheduled dues are not unpaid dues or an approved collection forecast. Do not enable financial posting to populate a dashboard.
3. Define project associations before enabling project filters. The current endpoint supplies no projects and accepts company/period only; the client leaves the project selector disabled. Do not silently apply a property scheme as a construction project filter.
4. Complete HTTPS and the deployment's CSP/session/Company/report checks, then test browser and native login/logout, uploads, protected downloads, saved/reopened locations, Google links and GPS on real devices. PR #28 reports the test server is still HTTP by IP; no HTTPS URL or live acceptance is assumed here. No TLS bypass was added.

The client has no authority to install Insights, activate Finance workflows or resolve legal/accounting gates. Existing records and the concurrent backend implementation remain preserved.
