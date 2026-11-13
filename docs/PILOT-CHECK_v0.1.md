# Existing pilot dataset verification v0.1

13 Nov 2026. Operational verification under G14 and G16; no new business rule.

Use `deploy/sidra-pilot-check.sh` when the twelve-month pilot dataset has already
been loaded into **Sidra Homes** on **sidra.local**:

```bash
bash /home/frappe/sidra/frappe-bench/apps/sidra_realestate/deploy/sidra-pilot-check.sh
```

Run as root or the frappe bench operator. The script uses the bench's Python,
calls `verify_pilot_demo` directly and checks that every expected submitted
voucher count equals its posted count. The existing Administrator, staging-flag,
manifest and foreign-GL checks remain in force. Original exceptions are printed
without the `bench execute` fallback that can obscure them with a `NameError`.
It prints the original reporting dates, changes no flags or records, runs no
loader and rolls back its database connection before closing. A refusal or
count mismatch exits nonzero. It never tries a repair or cleanup.

The observed test-site result on 13 Nov was 60 Sales Invoices, 35 Purchase
Invoices, 64 Payment Entries and one Journal Entry: 160 submitted vouchers.
These observations do not establish report balances or screen visibility.
The script labels ledger amounts, current operational counts and browser
checks as **NOT VERIFIED**. Use the printed period in the native reports;
Trial Balance may require separate fiscal-year selections.

## Why the old runbook stopped

`sidra-homes-run_v0.1.sh` invokes `sidra-homes-verify_v0.2.sh all`. That command
attempts to load the older ten-voucher finance demo before verifying anything.
With the pilot manifest present but no finance demo manifest, its first-load
guard refuses the existing Sales Invoices. That is an expected refusal, not
evidence that the pilot load failed. Neither `all` nor `populate` is an
existing-pilot verification command. The old runbook's fixed totals also
describe the ten-voucher dataset, not the twelve-month pilot.

Keep the old runbooks for their original workflow. Use the new check for an
existing pilot. No invoice, manifest, Company, file, backup, log or git stash
needs to be removed to resolve this refusal. On any failure, retain the
output for diagnosis and do not loosen guards or rerun a loader.
