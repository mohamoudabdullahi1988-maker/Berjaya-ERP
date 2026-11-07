# Sidra Owner/CEO Insights Starter v0.1

7 November 2026. Reporting-only implementation authorized by Mohamoud in this chat.
Requirements: SRS v2.0-DRAFT §3.6; SAL-01/03/13, INS-02/14, CON-04.
Source decisions: DECISIONS-AND-GATES v0.1, particularly G3 (no Murabaha), G4
(ERPNext is the only ledger), and the Finance posting gate. No business rules change.

## Delivery and ownership

This package generates an Insights **v3 Workbook export**, containing five SQL
queries, eight charts, and one private dashboard. It is not an installed ERPNext
report, a financial ledger, an approval workflow, or a running Insights instance.
It adds no hooks, patches, dependencies, schema changes, public endpoints, roles,
or edits to Claude's core functions. No app release/version bump is made for this
isolated integration package. Merge and deployment remain pending in this task.

Sidra schema reviewed: `develop` at `f2cd88eb6203ff359b21d7c6dde89cc84f78f9b2`.
Upstream format reviewed: Insights `version-3` at
`c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c`. This branch declares Frappe >=15,<17;
it is the candidate for Sidra v16. Do not use Insights `develop` for Sidra v16.
Actual installation, query execution, permissions and browser rendering on Sidra
remain to be verified. Check licenses (Insights AGPL-3.0) with the deployment owner.

## Dashboard and definitions

| Component | Exact basis | Limits |
| --- | --- | --- |
| Signed sales value | One row per submitted Sidra Sale Contract, `agreed_price`, by `signed_on` in the configured inclusive period | Agreed commercial value, not revenue/cash. Registered historical contracts use signing date, not registration date. |
| Sales by scheme | Submitted contract-unit `allocated_price`, grouped by scheme ID | Never sum the parent contract value after joining units. Reconcile allocations to parent totals. |
| Available units / inventory status | Current Sidra Unit status, valid unit/scheme Company, matching Company default currency | Current inventory, not historical as-of inventory; excludes missing/mismatched parents. No asking-value claim. |
| Gross scheduled dues next 30 days | Rows on eligible submitted installment contracts, from the day after cutoff through cutoff +30 inclusive | Includes stored Installment/Down payment/Fee rows. Before settlements, not unpaid balance or predicted cash. Separately recorded down payments have no due date and are omitted. |
| Construction stage exceptions | Active jobs (Contracted/In Progress/On Hold), recorded stage planned/actual end dates | Past planned end without actual end and incomplete/unknown completion, or actual end after planned end. Missing planned dates are unknown, not on schedule. No certified baseline or margin claim. |

Cash collected, overdue unpaid balances, cash balances, forecast margin and target
attainment are **unavailable**. There are no receipt or allocation fields in the
current Sidra Installment Line. Do not derive payments from `down_payment`,
`balance`, `amount_due`, the schedule or BOQ. BOQ is not actual cost. Don't replace
missing integrations with zero. ERPNext Payment Entries and approved allocations
must be connected and reconciled before enabling collection/arrears metrics.

Queries return record IDs for reconciliation, without KYC/contact data. Joining
contracts, unit allocations and schedule rows in one aggregate would multiply
values; these are deliberately separate queries. Same-day schedule rows retain
their unique row IDs. No changes to signed terms or posted documents occur.

## Generate the import file

From the repository root, using Python 3.10+ (Sidra uses 3.14):

```bash
python3 -m unittest discover -s integrations/insights/tests -v
python3 integrations/insights/build_workbook.py \
  --company 'Example Homes' --currency USD \
  --period-start 2026-11-01 --as-of 2026-11-07 \
  --data-source 'Site DB' \
  --exclude-scheme TEST-SCHEME \
  --output /tmp/sidra-owner-workbook.json
```

Replace Company, currency, dates, source name and exclusions with verified values.
The included `integrations/insights/examples/owner-workbook.json` is a generated
template for **Example Homes**, with no embedded customer data; it will not query
Sidra's real company unchanged. Generate a fresh file rather than editing SQL by
hand. Output creation refuses to overwrite an existing file.

One workbook has one fixed company/currency scope. Sales dates and the upcoming
schedule cutoff are fixed in the generated SQL. Regenerate for a new period;
refreshing the browser does not advance them. Inventory/stages use current records,
not a point-in-time reconstruction. Africa/Mogadishu business dates must be chosen
explicitly; the generator never infers dates from UTC.

`--exclude-scheme` accepts exact Sidra Scheme IDs, repeated as needed. It removes
inventory rows in those schemes and **whole contracts** containing any unit there
from sales/dues, avoiding misleading partial-contract totals. Contracts without
unit rows or with missing/cross-company unit/scheme links are also excluded.
Reconcile this eligible subset before sign-off. Construction jobs have no approved
scheme linkage; scheme exclusions do not filter jobs. There is no global Scheme
filter pretending to cover construction. Never infer Rayan/Safa/Hagbad membership
from text prefixes. Use real scheme records; no project names or price lists are seeded.

## Install and import on isolated staging (administrator)

First record actual `bench version` and `bench --site <site> list-apps`, resources,
backup/restore availability and existing Insights installation. Do not replace an
existing Insights checkout blindly. For a bench without Insights, a candidate path is:

```bash
bench --site <staging-site> backup --with-files
bench get-app --branch version-3 https://github.com/frappe/insights.git
```

Check out the reviewed upstream SHA above in `apps/insights`, then use the bench's
normal dependency installation/build procedure (`bench setup requirements`,
`bench --site <staging-site> install-app insights`, `bench build --app insights`).
These are staging instructions, not commands executed by this PR. Dependency
changes affect the bench; validate them in isolation before touching the shared VPS.
Do not upgrade Frappe/ERPNext, enable global Server Scripts, create demo data, or
change a site default as a side effect of adopting this package.

Verify Site DB (or the chosen datasource) connects and required tables are synced.
Import the generated file using Insights' workbook import flow. An administrator
can alternatively call the upstream `import_workbook` function from a bench console:

```python
import json
from pathlib import Path
from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook
payload = json.loads(Path('/tmp/sidra-owner-workbook.json').read_text())
workbook_name = import_workbook(payload)
frappe.db.commit()
print(workbook_name)
```

Run inside an initialized `bench --site <staging-site> console` as the intended
Insights owner; do not bypass document permissions. Import creates a **new** workbook
each time. It is not an idempotent deployment/update mechanism. Keep old workbooks
private and retire superseded copies deliberately after checking reconciliation.

## Permissions and sharing

Raw SQL is not proof of Frappe Company User Permission or record-permission enforcement.
The hardcoded Company clause prevents accidental mixed-company totals for this export;
it is not a substitute for authorization, and a query editor could change it.

Use the workbook initially only for an authorized owner/CEO with full access to the
selected company. Configure and verify Insights team/source/table permissions
(`Insights Settings.enable_permissions`) before granting staff access. With team
permissions off, Insights source/table access can be broad. Do not auto-grant Insights
Admin to the CEO. Share the dashboard read-only with named authorized users after
tests; keep workbook edit access restricted. No public links or organization-wide
sharing. The generator intentionally does not manage users or permissions.

Check anonymous, unrelated staff, other-company users, named CEO and report designer
against dashboard/query/chart URLs and exports, including attempts to change filters
or read the underlying tables. Decide which roles may export or edit queries. Don't
assume standard Desk permissions transfer automatically to BI queries.

## Staging acceptance and rollback

1. Run the local regression tests and a schema check on the same Sidra revision to
   be deployed. Check Claude's latest changes for removed/renamed fields first.
2. Import into Insights; confirm 5 source queries, 8 charts, 1 dashboard. Open every
   chart and inspect server logs for SQL/Ibis/import errors.
3. Reconcile one multi-unit contract and multiple same-day dues to source records;
   verify totals aren't multiplied. Check draft/cancelled/future-signing exclusions,
   wrong Company/currency and intentionally excluded test schemes.
4. Verify exact upcoming-window boundaries, zero versus empty/error states and
   separately recorded down payments. Failed chart refresh must not appear as zero.
5. Compare scheme sums to eligible contract sales; inventory to current unit lists;
   stage flags to recorded dates. Verify charts with >1,000 groups/rows and pagination;
   detail charts are limited to 1,000 and must not be mistaken for a complete register.
6. Test phone/desktop rendering, text visibility, links, refresh/cache behavior,
   source freshness, query timings and permissions above. There are no preinstalled
   record drilldown links; use retained record IDs and authorized native records.
7. Record evidence before enabling CEO access. Collections and financial cards stay
   unavailable until Claude supplies the approved integrations.

Removing this Git branch/package does not remove imported Insights objects. To
rollback the dashboard, revoke its shares and delete the identified imported
workbook through Insights' supported UI (which handles its linked objects). Do not
drop Sidra tables or uninstall Insights from a shared bench as a dashboard rollback.
Restore the staging backup only if the app installation itself needs reverting.

## Coordination with Claude

Only new paths under `integrations/insights/`, this versioned document and an isolated
test workflow are added. Core DocTypes, staff clients, financial logic, hooks,
migrations, shared CI, app version and changelog are unchanged. Shared-file release
metadata should be handled at integration rather than racing Claude's version bumps.
The CEO staff client remains independent; this package does not replace its API or
create a second ledger. Any field changes require rerunning these schema-based tests.

Local evidence: Python 3.12 / SQLite regression execution against repository DocType
metadata. This does **not** establish Python 3.14/Frappe/MariaDB/Insights runtime,
browser usability, security enforcement or installation success.

Sources: [Insights compatibility](https://github.com/frappe/insights/blob/c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c/pyproject.toml),
[workbook import/export](https://github.com/frappe/insights/blob/c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c/insights/insights/doctype/insights_workbook/insights_workbook.py),
[chart types](https://github.com/frappe/insights/blob/c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c/frontend/src2/types/chart.types.ts),
[permission implementation](https://github.com/frappe/insights/blob/c7dc954d8275756deb5ad24f7c35c3f3c2ca1a6c/insights/permissions.py).
