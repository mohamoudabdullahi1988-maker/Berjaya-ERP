#!/usr/bin/env bash
# Run as the bench operator on the explicitly authorized Sidra test VPS.
set -Eeuo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd /home/frappe/sidra/frappe-bench
trap 'echo "Stopped at line $LINENO; no successful upload is claimed."' ERR

test -f apps/sidra_realestate/sidra_realestate/demo_reporting.py
echo "Backing up the test site..."
bench --site sidra.local backup --with-files
bench --site sidra.local set-config sidra_allow_demo_data 1
bench --site sidra.local set-config sidra_finance_demo_site 1
bench --site sidra.local set-config sidra_allow_finance_demo_vouchers 1

echo "Creating/verifying fictional vouchers and staff dashboard source records..."
bench --site sidra.local execute sidra_realestate.demo_reporting.populate_and_verify
bench --site sidra.local clear-cache

echo "Open https://5.253.233.218/sidra-staff/"
echo "Select Sidra Homes; period Last 90 days; refresh."
echo "For financial statements, use the exact Company and original dates printed above."
