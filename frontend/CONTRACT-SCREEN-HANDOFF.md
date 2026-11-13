# Contract screen handoff

Workstream D, 13 November 2026. Base: frontend scaffold commit c62a510.
Only frontend files changed. No deployment, migrations, or business writes.
B and C must merge before rebasing onto develop and opening D's PR.
Version and CHANGELOG changes are deferred until that PR.

## Field mapping

- Reference: Sidra Sale Contract.name; customer: customer.
- Property: units[].unit and units[].scheme (Sidra Contract Unit).
- Status: docstatus, displayed as Draft / Confirmed / Cancelled.
- Agreement: signed_copy; date: signed_on (signed date, not upload date).
- Sale price: agreed_price; down payment: down_payment.
- Schedule comparison balance: amount_due, which accounts for down_payment_mode.
- Total: persisted schedule_total; never sum a potentially restricted subset.
- Schedule: schedule[].seq, due_date, amount (Sidra Installment Line).
- Installment payment status has no persisted field: displayed as Unavailable.

## Timeline integration

Single method constant in src/contracts.js:
sidra_realestate.api.workflow.get_contract_timeline.
C returns transaction as an object, supported/reason, and stage detail,
next_action, figures, skipped and unavailable in addition to the original brief.
Approval is Terms approval (Sales Manager), not Finance approval.
Stage order and state come exclusively from the response. Actions are not rendered.
No tokens added. Existing shell drawer reused and labelled Workflow.

## Verification

- npm test: 6 component/helper tests passed.
- npx vite build --config verify.config.js: build passed; outputs confined to .verify.
- python3 -m unittest discover -s sidra_realestate -p 'test_engine_*.py' -t .:
  98 existing tests passed.
- python3 frontend/tests/browser.py (from repo root, Vite on localhost:8080):
  isolated synthetic-response component tests passed at 1440px and 390px;
  workflow render/refresh, no horizontal overflow or page errors.
- Browser fixtures exist only in tests; no app demo path.
- Live-site checks a–f: not verified. No test-site access performed.
- No real SSC-2026-00001 response or real-role verification claimed.
- Frappe integration tests unavailable locally: bench is not installed.
- Standard production output build from a clean checkout remains unverified;
  verification config exercises the same Vue/Frappe UI compilation with local outputs.

Latest inspected B update changes brand.js and main.js, not the shell/route
interfaces D consumes. Rebase and rerun checks after B/C merge.
