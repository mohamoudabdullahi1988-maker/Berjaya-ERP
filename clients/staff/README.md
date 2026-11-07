# Sidra Homes staff clients

A small server-hosted staff dashboard, an Android system-WebView app, and a macOS WKWebView app. Claude owns the ERPNext backend/test server; this component does not modify the backend checkout.

**Status:** working fictional web preview and tested location geometry/API boundary. Server URL is not ready. Real dashboards require Claude's aggregate endpoint. The isolated location adapter is provided but not installed or integration-tested against a real Frappe site. Native builds must run on Android/macOS toolchains before distribution; source size is not an APK/app-size claim.

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

The screens cover Sales/lead pipeline, posted Payments and overdue aging, existing Construction Job KPIs, contracts, scheduled installments, and shared plot/site locations. KPI definitions and permission rules are in [the API contract](docs/API-CONTRACT.md). Nothing calculates penalties, refunds, revenue recognition or title obligations on the client.

## Native apps

- Android: `native/android`, Java using only platform APIs; no bundled Chromium, Flutter, Electron or JavaScript bridge. With JDK 21, Android SDK 35 and Gradle 8.11.1: `gradle -p native/android :app:assembleDebug :app:lintDebug`.
- macOS 13+: `native/macos/package.sh` builds a local ad-hoc signed `.app` using Swift/AppKit/WebKit. Developer ID signing, notarization and installer distribution are separate release steps.
- The included workflow defines both platform builds. It has not been run merely by adding it to this source tree.

At first launch, enter the administrator-provided HTTPS server origin. Both apps open `/sidra-staff/`; all sign-in and application logic remains there. Server changes need no app update unless the native capabilities change. Android includes explicit device-location permission and document upload/download via platform pickers. Mac uses WebKit's file panels and download delegate; device geolocation depends on OS/WebKit permission support, with coordinate entry always available. These native capabilities need actual device/macOS testing.

Downloads are only from the configured origin; Android streams to a user-selected destination and does not forward its session cookie through redirects. External HTTPS map links open the system browser. Invalid certificates and cleartext HTTP are not accepted. No production credentials or Google API secrets are in source.

## Deployment handover

Host `web/` at `/sidra-staff/` on Frappe's HTTPS origin, inject the real session CSRF token, and connect the response in `docs/API-CONTRACT.md`. Integrate the separately provided location adapter, or map it to an existing equivalent location field/API. Do not overwrite Claude's app entrypoints or hook files. The staff server must enforce all roles and Company permissions itself.

See [desktop preview](docs/screenshots/desktop-overview.png), [phone preview](docs/screenshots/mobile-overview.png), [payments](docs/screenshots/payments.png), [web location editor](docs/screenshots/web-location.png). Screenshots contain fictional data, not verified live financial figures.
