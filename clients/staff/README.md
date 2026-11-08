# Sidra Homes staff clients

A small server-hosted staff dashboard, an Android system-WebView app, and a macOS WKWebView app. Claude owns the ERPNext backend/test server; this component does not modify the backend checkout.

**Status (8 Nov 2026):** the executive UI is merged, and PR #28 provides the staff page, operational dashboard and location APIs in the Frappe app. The optional executive aggregate, approved targets/Finance source mappings, HTTPS deployment and actual device acceptance remain pending. Android debug assembly/lint and universal macOS packaging have passed prior CI; source size is not an installed-app-size claim. See the current [dashboard handover](docs/DASHBOARD-HANDOVER_v0.2.md) for verified behavior and remaining integration work.

## Preview

Node 24, no npm dependencies:

```sh
npm start
# open http://localhost:4173/?demo=1
npm test
npm run check
python -m unittest discover -s tests -p 'test_*.py' -v
node tools/browser-smoke.mjs
```

`?demo=1` is explicitly labelled fictional. Pins edited in preview are in-memory only. Without that parameter the page requests the live same-origin backend and shows failures honestly. The app keeps no local financial database and no offline private-data cache.

The executive overview covers six headline cards, server-supplied targets, monthly sales/collections, management decisions with supporting records, business exposure, scope filters and freshness. Preview filters are fixed and disabled; live filters request new server snapshots. The screens also cover Sales/lead pipeline, posted Payments and overdue aging, existing Construction Job KPIs, contracts, scheduled installments, and shared plot/site locations. KPI definitions and permission rules are in [the API contract](docs/API-CONTRACT.md) and [executive API v0.1](docs/EXECUTIVE-API_v0.1.md). Nothing calculates penalties, refunds, revenue recognition or title obligations on the client.

## Native apps

- Android: `native/android`, Java using only platform APIs; no bundled Chromium, Flutter, Electron or JavaScript bridge. With JDK 21, Android SDK 35 and Gradle 8.11.1: `gradle -p native/android :app:assembleDebug :app:lintDebug`.
- macOS 13+: `native/macos/package.sh` builds a universal (Apple Silicon/Intel), local ad-hoc signed `.app` using Swift/AppKit/WebKit. Developer ID signing, notarization and installer distribution are separate release steps.
- The repository workflow builds both platforms and runs the web/location tests. CI artifacts are test builds; signing/notarization and live-server/device acceptance are still required.

At first launch, enter the administrator-provided HTTPS server origin. Both apps open `/sidra-staff/`; all sign-in and application logic remains there. Server changes need no app update unless the native capabilities change. Android includes explicit device-location permission and document upload/download via platform pickers. Mac uses WebKit's file panels and download delegate; device geolocation depends on OS/WebKit permission support, with coordinate entry always available. These native capabilities need actual device/macOS testing.

Downloads are only from the configured origin; Android streams to a user-selected destination and does not forward its session cookie through redirects. External HTTPS map links open the system browser. Invalid certificates and cleartext HTTP are not accepted. No production credentials or Google API secrets are in source.

## Deployment handover

PR #28 serves `web/` at `/sidra-staff/` with session CSRF injection and integrates the location APIs/native fields in the app. Deploy through the normal migrate/build process; do not copy the historical isolated adapter over Claude's implementation or install duplicate fields. Complete the HTTPS deployment and executive response described in `docs/API-CONTRACT.md` and `docs/EXECUTIVE-API_v0.1.md`. The staff server must enforce all roles and Company permissions itself.

See [desktop preview](docs/screenshots/desktop-overview.png), [phone preview](docs/screenshots/mobile-overview.png), [payments](docs/screenshots/payments.png), [web location editor](docs/screenshots/web-location.png). Screenshots contain fictional data, not verified live financial figures.
