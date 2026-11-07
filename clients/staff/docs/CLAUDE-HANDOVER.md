# Client handover for Claude — 7 Nov 2026

User allocation: Claude codes the backend/test server; Codex codes the Android/macOS staff clients and shared web dashboards. Staff only. Server URL: not ready.

The shared UI is plain HTML/CSS/ES modules, approximately 44 KB before compression. No framework/runtime is bundled. The Android Java shell uses the system WebView; the macOS Swift shell uses the system WKWebView. The main application stays on your server at `/sidra-staff/`.

Please review `API-CONTRACT.md`, implement/reuse the permission-filtered dashboard aggregate endpoint, and serve the UI under the same origin with session CSRF injection. Payments must derive from posted ERPNext payments/allocation; leave the section unavailable until Finance data is real. Job KPIs must derive from existing jobs/milestones/inspections. Sales value is not revenue.

The user separately requested Google Maps/Earth locations in web and both apps. `integration/frappe/sidra_realestate/api/locations.py` and `location_geometry.py` provide the scoped adapter. Review/integrate it without duplicating any location fields you may have added. Use native Geolocation Custom Fields, preserve existing GPS text, check parent read/write/Company permissions, refuse stale edits, and export Point KML. Google external links need no key; an embedded basemap needs a restricted Maps Embed browser key.

Verified here: Node source/contract checks, 12 Python geometry/adapter boundary tests (stubbed Frappe, not integration tests), desktop and phone Chromium smoke tests, explicit demo-only behavior, invalid coordinate refusal and no silent demo fallback on live failure. Browser screenshots are in `screenshots/`.

Not verified: live Frappe/API/session/Company integration, GPS on actual devices, Android SDK build, macOS build/signing/notarization, exact installed app size. The current Linux environment has no Android SDK/Gradle or macOS toolchain and very little free disk. CI definitions are included to build on the appropriate runners. No test-server endpoint has been invented, no existing backend files were edited, and no data was posted to the ERP.

Next: agree the aggregate endpoint/cohort definitions; install and test the location adapter on your test server; provide HTTPS URL; run the platform builds and test login/logout, CSRF, uploads, protected downloads, expired sessions, map links and GPS. Review the source before any production release.
