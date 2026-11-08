# Sidra Insights native validation v0.1

8 November 2026. Continuation of the reporting-only work in PR #27.
Companion to [INSIGHTS-CEO_v0.1.md](INSIGHTS-CEO_v0.1.md); dashboard definitions,
Finance gates and operational ownership are unchanged.

## Purpose

The original 12 reporting regression tests run against SQLite. The new
`native-insights` CI job installs pinned Frappe v16.55.2, ERPNext v16.53.0,
Sidra from the PR and Insights at
`c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c`, using Python 3.14, Node 24 and
MariaDB 11.8. It exercises native workbook import and MariaDB/Ibis execution.
No dependency is added to Sidra's app package or shared deployment workflow.

The job uses a disposable `insights_ci` site on the GitHub runner. It does not
connect to Sidra's VPS and requires no production credentials. The smoke script
refuses other site names or a missing `SIDRA_INSIGHTS_DISPOSABLE_SITE=1` flag.

## Evidence expected

- Five source queries, eight private charts, one private dashboard imported.
- Native results: one submitted $1,000 contract, two unit allocations totaling
  $1,000, three current units including one available, three upcoming rows
  totaling $400, and one construction stage date exception.
- Due-today and day-31 rows excluded; same-day Installment/Fee rows retained;
  another company's unit excluded.
- Named read-only viewer can read the imported workbook/dashboard/charts/source
  queries but cannot edit. Guest and an unrelated Insights User cannot read them.
- Test logs retained as `insights-native-test-evidence` on the workflow run.

Fixtures use direct inserts only on that disposable site to isolate reporting
from Claude's legal-confirmation, accounts and sales workflows. They are synthetic
and are **not** examples of how to register real contracts. No financial vouchers,
penalties, refunds, title transfers or production imports are performed.

## Remaining operational checks

Passing this job establishes only the checks it executes. It does not validate
browser rendering or chart data-query generation by the frontend, mobile layout,
HTTP/export authorization, Company User Permissions inside BI, production source
completeness, source freshness or performance at real data volumes. Test those on
isolated staging using the deployment guide before giving the owner access.

The generator remains an explicit dated export, not an automatic updater. The
sample company and dates must be replaced with verified staging values.
Collections/arrears/cash/margin stay unavailable until approved Finance integration.

## Coordination

Continues `feature/reporting-insights-ceo` and PR #27; no second feature branch.
Only the existing isolated Insights workflow and new Insights-specific files are
changed. The PR remains draft, unmerged and undeployed pending integration evidence.
