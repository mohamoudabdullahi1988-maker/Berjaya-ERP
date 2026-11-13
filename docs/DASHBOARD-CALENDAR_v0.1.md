# Staff dashboard calendar and pilot sources v0.1

13 Nov 2026. Implements the owner's dashboard request; G14/G16, existing
permissions and production posting gates are unchanged.

## Company and finance sources

The staff dashboard selector omits **Sidra Demo Homes** and **Sidra Finance
Demo - Fictional**, and prefers **Sidra Homes** among readable Companies.
This is a selector change; the Company masters, vouchers and files remain.

The native finance adapter previously required `sidra-finance-demo-v1.json`.
The observed VPS contains the twelve-month `sidra-pilot-demo-v1.json` instead,
with 60 Sales Invoices and 64 Payment Entries. The adapter now accepts either
manifest or both and validates the complete union of readable submitted
invoices/payments against their owned IDs. A missing/malformed manifest,
duplicate ownership, foreign/partial cohort, missing monetary field, unexpected
currency or unreadable accounting record remains unavailable. No permissions
are granted. The existing staging flags are still required.

Posted Receive Payment Entries supply cash and trends; native invoice
outstanding amounts supply current overdue invoice balances and aging. These
fictional service invoices are not linked to commercial installment contracts.
Nothing here creates that allocation or enables production posting.

## Installment calendar

`GET sidra_realestate.api.staff_dashboard.get_installment_calendar`
accepts `company` and `month=YYYY-MM`. It requires staff access and a readable
Company, then selects only readable submitted installment contracts of that
Company/currency, signed on or before the business day in Africa/Mogadishu.
Child rows are read only for these authorized parents and their schedule field.
Draft, cancelled, future-signed, foreign-Company and foreign-currency parents
are excluded. Every row in the inclusive requested month is returned; the
20-row upcoming-preview limit does not apply. Invalid months are rejected.

The response includes `company_id`, `currency`, `month`, `today`,
`basis: gross_schedule`, `allocation_available: false`, `events`, `days` and
`summary`. Summary keys are `month`, `today`, `past_due`, `upcoming`, each with
an exact decimal amount and row count. Missing/invalid amounts yield null,
not zero. Empty permitted cohorts are a known zero. Events carry a stable row
ID, contract ID/reference, buyer display, due date, type, agreed amount and
server-computed `date_state` (`past_due`, `today`, `upcoming`).

Calendar and list share this complete month. Month navigation reloads the
server cohort; date/status/search filters change its presentation. Daily
totals come from the server and are hidden when a search/status filter would
make them appear to describe a partial day. Clicking a date opens its list.
Scope changes and failed/late requests clear prior results; live failures
never substitute preview data.

**Past scheduled dates are unreconciled, not verified unpaid installments.**
Receipt and overdue-invoice cards below the calendar follow the dashboard's
selected reporting period/current invoice balances and remain separate from
the selected schedule month. Their reasons are shown if finance is unavailable.

## Construction

Open jobs include enquiries and quoted work as well as active jobs; recorded
status counts explain why the narrower active/completed cards may be zero.
No job status is rewritten. The executive headline now uses the existing
recorded overdue-milestone evidence. The original `projects_on_schedule` API
field stays unavailable without an approved baseline. The stage progress
column states that its current figure is the average recorded stage percentage.

## Deployment and acceptance

After this PR is merged and the test bench is backed up, fast-forward its app
to `develop`, run `bench --site sidra.local migrate`,
`bench build --app sidra_realestate`, then restart the normal bench services.
**Do not use the old population runbook**: no data load is required. Hard
refresh `/sidra-staff/`. Existing Android/macOS shells load the shared page.

Check as an accounting-permitted staff user: only the intended Company options,
nonzero pilot receipt/invoice figures reconciled to native reports, the complete
month in Calendar and List, date/status/search filters, previous/next months,
source links and narrow/mobile screens. A role without accounting permissions
must see an unavailable reason, not financial values or invented zeros.
Pure tests and HTTP browser fixtures are not VPS deployment evidence.
