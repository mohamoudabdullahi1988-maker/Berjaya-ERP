# Berjaya frontend v0.2

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
- No demo or in-memory data. A failed request shows the failure, not a fallback.
- `yarn dev` is not wired to a session yet: the boot data only exists on the built page.

## Screens (v0.2)

| Route | Reads |
| --- | --- |
| `/berjaya/properties` | Sidra Unit (REST) |
| `/berjaya/contracts`, `/contracts/<name>` | Sidra Sale Contract (REST); workflow panel from `api.workflow.get_contract_timeline` |
| `/berjaya/collections` | `api.staff_dashboard.get_installment_calendar` |
| `/berjaya/construction`, `/construction/<name>` | Sidra Construction Job (REST) |
| `/berjaya/finance` | `api.staff_dashboard.get_dashboard` (payments), Sales Invoice and Payment Entry (REST) |
| `/berjaya/dashboard` | not built yet |

All screens are read-only. Shared pieces: `src/format.js` (display only), `src/list.js` (paged
lists), `src/workflow.js` (how a stage is drawn), `src/panel.js` (the right-hand panel).

## Checks

```bash
cd frontend && yarn test                                   # unit tests (node --test)
(cd frontend && yarn dev --port 8080 --host 127.0.0.1) &   # then, from the repository root:
python3 frontend/tests/browser.py                          # every screen at 1440px and 390px
```

The browser check answers the API with synthetic records that live only in the test.
