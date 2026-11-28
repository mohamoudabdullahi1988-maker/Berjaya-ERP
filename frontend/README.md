# Berjaya frontend v0.3

14 Nov 2026 · the Berjaya interface served at `/berjaya` (Vue 3, Vite, Frappe UI).

"Berjaya" is the software; "Sidra" is the client company and comes from the server.

## Build

```bash
bench build --app sidra_realestate      # on a bench: installs and builds this folder too
# or, from a clean checkout without a bench:
yarn install --frozen-lockfile && yarn build      # run at the repository root
```

The build writes `sidra_realestate/public/berjaya/` and `sidra_realestate/www/berjaya.html`.
Neither is committed. `sidra_realestate/www/berjaya.py` supplies the session boot data.

## Rules

- Sign-in is the existing Frappe session. No tokens, nothing in local storage.
- Colours and fonts are defined once, in `src/tokens.css`. Fonts are bundled, not fetched.
- The server says which sections and fields a user may see (`window.berjaya_boot`). The
  frontend shows that; it decides no permission and holds no business rule of its own.
- A value the user may not see reads "Unavailable": never zero, never a partial figure.
- No demo or in-memory data on record screens. A failed request shows the failure, not a fallback.
- Investment contains a labelled fictional funding demonstration. All shared dashboards use
  authorized live sources (G39).
- `yarn dev` is not wired to a session yet: the boot data only exists on the built page.

## Screens

Staff land on `/berjaya` after signing in. The shared header opens ERPNext Desk. Saved transactions
offer a Workflow window with their recorded progress.

| Route | Reads |
| --- | --- |
| `/berjaya` | Priority reports and transaction shortcuts |
| `/berjaya/executive`, `/build/<tab>`, `/design/<tab>`, `/real-estate/<tab>`, `/crm`, `/finance-overview` | Live workspace reports, configured in `src/showcase/live.js` |
| `/berjaya/investment` | Labelled fictional funding demonstration |
| `/berjaya/dashboard` | `api.staff_dashboard.get_dashboard` |
| `/berjaya/properties`, `/properties/price-history` | Sidra Unit; Sidra Unit Price History |
| `/berjaya/customers`, `/customers/kyc` | Customer (with related records); Sidra Customer KYC |
| `/berjaya/sales/reservations`, `/sales/quotations` | Sidra Reservation; Sidra Sale Quotation |
| `/berjaya/contracts`, `/contracts/title-transfers` | Sidra Sale Contract (workflow window: `api.record_workflow.get_timeline`); Sidra Title Transfer |
| `/berjaya/collections` | `api.staff_dashboard.get_installment_calendar` |
| `/berjaya/construction` and `/quotations`, `/boq-revisions`, `/variations`, `/inspections` | Sidra Construction Job and its work records |
| `/berjaya/finance` | `get_dashboard` (payments), Sales Invoice, Payment Entry |

Each list ends in `/<name>` for one record. Lists and record pages are described in
`src/records.js` (keys match `LISTS` in `www/berjaya.py`); `RecordList.vue` and
`RecordDetail.vue` draw them. Shared pieces: `src/format.js` (display only), `src/list.js` (paged
lists), `src/workflow.js` (how a stage is drawn), `WorkflowWindow.vue` (the transaction dialog).

## Checks

```bash
cd frontend && yarn test                                   # unit tests (node --test)
(cd frontend && yarn dev --port 8080 --host 127.0.0.1) &   # then, from the repository root:
python3 frontend/tests/browser.py                          # every screen at 1440px and 390px
```

The browser check answers the API with synthetic records that live only in the test.
