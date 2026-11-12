# Sidra fictional financial demonstration v0.1

> **Superseded by [FINANCE-DEMO_v0.2.md](FINANCE-DEMO_v0.2.md) (12 Nov 2026, decision G12).** Kept for the record; the loader no longer uses the separate Company described here.

9 Nov 2026. User request: “Can you upload sample data so that financial reports and dashboards shows something”. Implements a **demo-only exception** to the prototype's voucher restriction, not a production accounting decision (SRS §3.6, G4). ERPNext remains the only ledger.

## Scope and isolation

`sidra_realestate.finance_demo.create_finance_demo_data` is a manual Administrator-only bench entrypoint, never a migration hook, scheduler or whitelisted HTTP API. It creates the fixed **Sidra Finance Demo - Fictional** Company (SFD), with no parent Company, USD and a native standard chart plus six clearly named demo accounts. It refuses an existing Company without its private ownership manifest, an abbreviation/master collision, or a changed voucher set/balance. Reruns return the same IDs and original dates, without reposting or advancing the schedule. Setup and posting share a transaction; failures roll back, including private-file callbacks. Run it in a fresh bench command, not inside another transaction.

No existing records are edited. No roles or permissions are granted. Do not consolidate the fictional Company with real companies or use these service transactions as an approved property/land revenue-recognition policy. Contract-to-invoice/receipt mapping, deposits, taxes, refunds, title transfer, penalties and production posting controls remain undecided/disabled. This sample has no deposits, fees, interest, tax, FX or rounding adjustment; USD integer amounts reconcile exactly.

## Load on the connected test site

After deploying this version of the app to an identified **test site**, run as its bench operator:

```bash
bench --site <test-site> set-config sidra_allow_demo_data 1
bench --site <test-site> set-config sidra_finance_demo_site 1
bench --site <test-site> set-config sidra_allow_finance_demo_vouchers 1
bench --site <test-site> execute sidra_realestate.finance_demo.create_finance_demo_data
bench --site <test-site> execute sidra_realestate.finance_demo.verify_finance_demo
```

The returned JSON includes voucher IDs, original date range, expected account balances, operational record IDs and native report links. The private Company attachment `sidra-finance-demo-v1.json` preserves this registry. Keep all three flags enabled while viewing demo finance on the staff dashboard; disable them after the demonstration to disable the loader and demo adapter (submitted vouchers remain in native reports).

Sign in with an existing authorized Administrator or management account with **native Sales Invoice and Payment Entry read permissions**. Select **Sidra Finance Demo - Fictional** on `/sidra-staff/`; do not use the in-memory `?demo=1` preview to verify persisted data. A Sidra GM role alone does not grant access to accounting. Financially restricted users get unavailable values rather than partial sums or zero. No fake fallback is used on request failure.

Open the returned General Ledger, Trial Balance, Profit and Loss Statement, Balance Sheet, Accounts Receivable and Accounts Payable links in ERPNext. The P&L/BS links use the full sample date range, not just the current month. TB is one fiscal year at a time: if the sample crosses New Year, its link opens the latest year; use the returned fiscal-year names to inspect the previous year separately. Native ERPNext report permissions still apply. Android/macOS require HTTPS; this work does not relax TLS for the old HTTP-only test IP.

## Fictional transactions and expected evidence

Dates are relative to first load: owner capital at day −45; sales invoices at −45/−20/−8 with due dates −15/−5/+15; purchases at −12/−5, due −2/+10. All four payments are posted on load day, so current-month collections show even early in a month.

| Measure | Expected USD |
| --- | ---: |
| Owner capital | 100,000 |
| Submitted non-stock service sales invoices (3) | 70,000 |
| Customer receipts (25,000 partial + 10,000 full) | 35,000 |
| Purchase invoices / expense (2) | 20,000 |
| Supplier payments (10,000 partial + 2,000 full) | 12,000 |
| Bank balance | 123,000 |
| Receivables (15,000 overdue + 20,000 future) | 35,000 |
| Payables | 8,000 |
| Net profit over full sample date range | 50,000 |
| Assets / liabilities / capital including profit | 158,000 / 8,000 / 150,000 |
| GL posted debit / credit totals | 237,000 / 237,000 |

The native invoice due cohort is 50,000, settled 35,000: **70%** collection rate at first load. One invoice is overdue by 15 days with 15,000 outstanding; its aging changes naturally as time passes. The dashboard explicitly says **Overdue invoices (demo)**, never contract arrears. Cash is native Receive Payment Entry value, not invoiced revenue or schedule value. Its drilldown opens the native Payment Entry list filtered to submitted customer receipts in the selected Company/period. The overdue drilldown opens native Accounts Receivable, where due dates and unpaid future invoices remain visible for context. Targets stay unset.

The same Company also has three fictional plots: one on a separately registered external commercial contract of 30,000, two Available with total asking value 22,000. Its actual schedule is three 10,000 installments at days +5/+35/+65. A private text original explicitly says it is fictional; no contract document is generated. This commercial example is **independent of** the 70,000 service invoice example: there is no implied allocation between them. Two fictional leads and one existing construction Job with 40% recorded progress / a date exception populate operational sections. Pipeline conversion and approved baseline performance stay unavailable.

## Verification and deployment status

Integration tests exercise disabled/non-Administrator guards, rollback after native posting, refusal to adopt an unrelated Company, persisted ten-voucher balances, repeat protection, native GL/TB/P&L/BS output, invoice settlement, financial permission refusal/partial-cohort refusal, and dashboard-to-native amounts. The saved external contract is reopened from the DB to verify private original, schedule and approval without document generation.

**A passing disposable CI demo is not evidence of a VPS upload.** At implementation start, this session had no test-server URL, configured SSH/VPN/HTTP identity or secrets. Deployment, upload and visible test-site acceptance remain pending until the test server is connected. Never paste credentials into chat; configure access in environment settings. No data is loaded automatically on install/migrate.

Rollback: disable the flags and revert app code to remove the adapter; existing posted demo vouchers remain. No destructive cleanup command is included. Prefer restoring/deleting an entirely disposable test site when the demo is no longer needed; do not delete real-company records or directly edit GL tables.
