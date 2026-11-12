#!/usr/bin/env bash
# =====================================================================
# sidra-homes-verify_v0.2.sh
# Part 2 runbook + verification for the Sidra Homes retarget
# Version: v0.2   Date: 2026-11-12   Site: sidra.local
# v0.2: the 60-unit check leaves out the loader's three added fictional plots
#       (scheme SHD-FICTIONAL) and reports them separately; the schedule
#       table is `tabSidra Installment Line`.
#
# Subcommands (run as root; bench steps drop to the frappe user):
#   backup     step 1 - full backup with files, prints the path
#   deploy     step 2 - report commit hash, migrate   (pull is NOT automated)
#   populate   step 3 - run the population script
#   inventory  step 4 - list what the two old demo Companies contain
#   verify     verification sweep, pass/fail with observed numbers
#   all        backup -> deploy -> populate -> inventory -> verify
#
# RULES ENFORCED BY THIS SCRIPT
#   * Backup runs before anything else and aborts the chain if it fails.
#   * Never touches the git stash. `git stash list` is read-only.
#   * Never deletes, merges or renames any Company.
#   * Never edits GL tables. All SQL below is SELECT-only.
#   * On a guard refusal it stops and prints the exact message.
#   * Anything it cannot determine prints NOT VERIFIED, never a guess.
# =====================================================================
set -uo pipefail

SITE=sidra.local
BENCH=/home/frappe/sidra/frappe-bench
APP=sidra_realestate
FRAPPE_USER=frappe
COMPANY="Sidra Homes"
OLD1="Sidra Demo Homes"
OLD2="Sidra Finance Demo - Fictional"
EXPECT_UNITS=60
DEMO_SCHEME=SHD-FICTIONAL
LOG=/root/sidra-homes-verify.log

exec > >(tee -a "$LOG") 2>&1
echo "=== sidra-homes-verify_v0.2.sh  ${1:-verify}  $(date -Is) ==="
[ "$(id -u)" -eq 0 ] || { echo "FATAL: run as root (bench steps drop to $FRAPPE_USER)"; exit 1; }
say(){ echo; echo "---- $* ----"; }
die(){ echo "FATAL: $*"; exit 1; }
asfrappe(){ sudo -u "$FRAPPE_USER" -H bash -lc "cd $BENCH && $1"; }

# SELECT-only SQL helper. Refuses anything that is not a SELECT.
sql(){
  case "$(echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//')" in
    select*) ;;
    *) echo "REFUSED non-SELECT statement"; return 1 ;;
  esac
  asfrappe "bench --site $SITE mariadb --skip-column-names -e \"$1\"" 2>/dev/null | tail -n +1
}

# Print "PASS/FAIL  label  observed=X expected=Y"
check_num(){ # label observed expected
  local label="$1" obs="$2" exp="$3"
  if [ -z "$obs" ] || [ "$obs" = "NULL" ]; then
    printf '  NOT VERIFIED  %-42s observed=<no value returned>\n' "$label"; return
  fi
  # integer-compare after stripping decimals
  local o e; o=$(printf '%.0f' "$obs" 2>/dev/null || echo "$obs"); e=$(printf '%.0f' "$exp")
  if [ "$o" = "$e" ]; then printf '  PASS  %-42s observed=%s expected=%s\n' "$label" "$o" "$e"
  else                      printf '  FAIL  %-42s observed=%s expected=%s\n' "$label" "$o" "$e"; fi
}

# =====================================================================
backup() {
  say "STEP 1 - full backup with files (runs before anything else)"
  local out; out=$(asfrappe "bench --site $SITE backup --with-files" 2>&1); echo "$out"
  echo "$out" | grep -qi "error\|traceback" && die "backup failed - STOPPING, nothing else run"
  say "Backup paths"
  echo "$out" | grep -iE "config|database|public|private|backup" || true
  ls -lht "$BENCH/sites/$SITE/private/backups" 2>/dev/null | head -8
  echo
  echo "REPORT THIS PATH: $BENCH/sites/$SITE/private/backups"
}

# =====================================================================
deploy() {
  say "STEP 2 - commit hash and migrate"
  echo "NOTE: this script does NOT pull. Check out the merged develop commit yourself,"
  echo "      then re-run. The stash is never touched."
  say "git state of $APP (read-only)"
  asfrappe "cd apps/$APP && git rev-parse HEAD"
  asfrappe "cd apps/$APP && git log -1 --oneline --no-decorate"
  asfrappe "cd apps/$APP && git status --short --branch | head -20"
  echo "-- stash list (READ ONLY, never applied or dropped):"
  asfrappe "cd apps/$APP && git stash list" || true

  say "App versions"
  asfrappe "bench version" 2>&1 | head -20

  say "migrate"
  local out; out=$(asfrappe "bench --site $SITE migrate" 2>&1); echo "$out" | tail -40
  echo "$out" | grep -qiE "traceback|error:" && die "migrate failed - STOPPING. Exact message above."
  echo
  echo "REPORT THIS COMMIT: $(asfrappe "cd apps/$APP && git rev-parse HEAD")"
}

# =====================================================================
populate() {
  say "STEP 3 - population as the bench operator"
  echo "Flags (test site only):"
  asfrappe "bench --site $SITE set-config sidra_allow_demo_data 1"
  asfrappe "bench --site $SITE set-config sidra_finance_demo_site 1"
  asfrappe "bench --site $SITE set-config sidra_allow_finance_demo_vouchers 1"

  say "finance demo loader"
  local out rc
  out=$(asfrappe "bench --site $SITE execute $APP.finance_demo.create_finance_demo_data" 2>&1); rc=$?
  echo "$out"
  if [ $rc -ne 0 ] || echo "$out" | grep -qiE "refus|traceback|error"; then
    echo
    echo "=================== STOPPED - GUARD OR ERROR ==================="
    echo "The loader did not complete. Exact message is printed above."
    echo "Do NOT loosen a flag or retry. Report this message as-is."
    echo "================================================================"
    exit 1
  fi

  say "verify_finance_demo (authoritative registry JSON)"
  asfrappe "bench --site $SITE execute $APP.finance_demo.verify_finance_demo" 2>&1

  say "demo_reporting.populate_and_verify"
  asfrappe "bench --site $SITE execute $APP.demo_reporting.populate_and_verify" 2>&1
}

# =====================================================================
inventory() {
  say "STEP 4 - contents of the two old demo Companies (NOTHING is removed)"
  for C in "$OLD1" "$OLD2"; do
    echo
    echo "### $C"
    echo -n "  GL entries (submitted, not cancelled): "
    sql "SELECT COUNT(*) FROM \`tabGL Entry\` WHERE company='$C' AND is_cancelled=0;"
    echo -n "  distinct vouchers: "
    sql "SELECT COUNT(DISTINCT CONCAT(voucher_type,'|',voucher_no)) FROM \`tabGL Entry\` WHERE company='$C' AND is_cancelled=0;"
    echo -n "  Sales Invoices (submitted): "
    sql "SELECT COUNT(*) FROM \`tabSales Invoice\` WHERE company='$C' AND docstatus=1;"
    echo -n "  Purchase Invoices (submitted): "
    sql "SELECT COUNT(*) FROM \`tabPurchase Invoice\` WHERE company='$C' AND docstatus=1;"
    echo -n "  Payment Entries (submitted): "
    sql "SELECT COUNT(*) FROM \`tabPayment Entry\` WHERE company='$C' AND docstatus=1;"
    echo -n "  Sidra Units: "
    sql "SELECT COUNT(*) FROM \`tabSidra Unit\` WHERE company='$C';"
    echo -n "  Sidra Sale Contracts: "
    sql "SELECT COUNT(*) FROM \`tabSidra Sale Contract\` WHERE company='$C';"
  done
  cat <<'NOTE'

PROPOSED CLEANUP ORDER - requires Mohamoud's written approval before ANY removal:
  1. Confirm Sidra Homes verification is fully green and has been reviewed.
  2. Take a fresh backup with files, kept off-server.
  3. "Sidra Finance Demo - Fictional" first - it is voucher-only and has no
     operational records depending on it.
  4. "Sidra Demo Homes" second - it carries units and contracts referenced by
     the section 5 demonstration checklist, so retire it only once those
     walkthroughs have been re-pointed at Sidra Homes.
  5. Cancel-then-delete vouchers through the ERPNext UI. Never DELETE from GL
     tables directly.
NOTHING ABOVE HAS BEEN EXECUTED. This is a proposal only.
NOTE
}

# =====================================================================
verify() {
  say "VERIFICATION - Company: $COMPANY"

  echo
  echo "[1] Units"
  local units; units=$(sql "SELECT COUNT(*) FROM \`tabSidra Unit\` WHERE company='$COMPANY' AND scheme<>'$DEMO_SCHEME';")
  check_num "existing units present" "$units" "$EXPECT_UNITS"
  echo "      unchanged-check (modified timestamps newer than 1h):"
  local touched; touched=$(sql "SELECT COUNT(*) FROM \`tabSidra Unit\` WHERE company='$COMPANY' AND scheme<>'$DEMO_SCHEME' AND modified > NOW() - INTERVAL 1 HOUR;")
  if [ "${touched:-}" = "0" ]; then echo "  PASS  no unit modified in the last hour"
  elif [ -z "${touched:-}" ]; then echo "  NOT VERIFIED  could not read unit modified times"
  else echo "  FAIL  $touched unit(s) modified in the last hour - investigate before proceeding"; fi

  check_num "added fictional plots ($DEMO_SCHEME)" \
    "$(sql "SELECT COUNT(*) FROM \`tabSidra Unit\` WHERE company='$COMPANY' AND scheme='$DEMO_SCHEME';")" 3

  echo
  echo "[2] Vouchers and GL totals"
  check_num "distinct submitted vouchers" \
    "$(sql "SELECT COUNT(DISTINCT CONCAT(voucher_type,'|',voucher_no)) FROM \`tabGL Entry\` WHERE company='$COMPANY' AND is_cancelled=0;")" 10
  check_num "GL debit total" \
    "$(sql "SELECT COALESCE(SUM(debit),0) FROM \`tabGL Entry\` WHERE company='$COMPANY' AND is_cancelled=0;")" 237000
  check_num "GL credit total" \
    "$(sql "SELECT COALESCE(SUM(credit),0) FROM \`tabGL Entry\` WHERE company='$COMPANY' AND is_cancelled=0;")" 237000

  echo
  echo "[3] Amounts"
  check_num "revenue (submitted sales invoices)" \
    "$(sql "SELECT COALESCE(SUM(grand_total),0) FROM \`tabSales Invoice\` WHERE company='$COMPANY' AND docstatus=1;")" 70000
  check_num "expenses (submitted purchase invoices)" \
    "$(sql "SELECT COALESCE(SUM(grand_total),0) FROM \`tabPurchase Invoice\` WHERE company='$COMPANY' AND docstatus=1;")" 20000
  check_num "customer receipts" \
    "$(sql "SELECT COALESCE(SUM(paid_amount),0) FROM \`tabPayment Entry\` WHERE company='$COMPANY' AND docstatus=1 AND party_type='Customer';")" 35000
  check_num "supplier payments" \
    "$(sql "SELECT COALESCE(SUM(paid_amount),0) FROM \`tabPayment Entry\` WHERE company='$COMPANY' AND docstatus=1 AND party_type='Supplier';")" 12000
  check_num "bank balance" \
    "$(sql "SELECT COALESCE(SUM(gl.debit-gl.credit),0) FROM \`tabGL Entry\` gl JOIN \`tabAccount\` a ON a.name=gl.account WHERE gl.company='$COMPANY' AND gl.is_cancelled=0 AND a.account_type='Bank';")" 123000
  check_num "receivables" \
    "$(sql "SELECT COALESCE(SUM(gl.debit-gl.credit),0) FROM \`tabGL Entry\` gl JOIN \`tabAccount\` a ON a.name=gl.account WHERE gl.company='$COMPANY' AND gl.is_cancelled=0 AND a.account_type='Receivable';")" 35000
  check_num "payables" \
    "$(sql "SELECT COALESCE(SUM(gl.credit-gl.debit),0) FROM \`tabGL Entry\` gl JOIN \`tabAccount\` a ON a.name=gl.account WHERE gl.company='$COMPANY' AND gl.is_cancelled=0 AND a.account_type='Payable';")" 8000

  echo
  echo "[4] SSC-2026-00001 and its schedule"
  local ssc; ssc=$(sql "SELECT COUNT(*) FROM \`tabSidra Sale Contract\` WHERE name='SSC-2026-00001';")
  if [ "${ssc:-0}" = "1" ]; then
    echo "  PASS  SSC-2026-00001 exists"
    echo -n "      installment rows: "
    sql "SELECT COUNT(*) FROM \`tabSidra Installment Line\` WHERE parent='SSC-2026-00001';" \
      || echo "NOT VERIFIED (child doctype name differs - check the schedule table name)"
  elif [ -z "${ssc:-}" ]; then echo "  NOT VERIFIED  could not query tabSidra Sale Contract"
  else echo "  FAIL  SSC-2026-00001 not found"; fi

  echo
  echo "[5] Foreign-GL guard sanity (should be 0 once only demo vouchers exist)"
  echo -n "      vouchers in $COMPANY outside the expected 10: "
  sql "SELECT GREATEST(COUNT(DISTINCT CONCAT(voucher_type,'|',voucher_no))-10,0) FROM \`tabGL Entry\` WHERE company='$COMPANY' AND is_cancelled=0;"

  cat <<NOTE

[6] MANUAL - cannot be automated (needs an authenticated browser session)
    Report these yourself as pass/fail:
      /sidra-staff/  Company "$COMPANY", Last 90 days
         -> Contracts, Sales, Payments, Construction show PERSISTED records.
            Do NOT use ?demo=1 - the in-memory preview is not evidence.
      Open for "$COMPANY" and confirm the printed date range on each:
         General Ledger, Trial Balance, Profit and Loss Statement,
         Balance Sheet, Accounts Receivable, Accounts Payable
      Note: Trial Balance is one fiscal year at a time. If the sample crosses
      New Year, inspect the previous year separately using the fiscal-year
      names returned by verify_finance_demo.

NOTE
  say "VERIFY DONE"
  echo "Any line above reading NOT VERIFIED must be reported as not verified."
  echo "Log: $LOG"
}

case "${1:-verify}" in
  backup) backup ;;
  deploy) deploy ;;
  populate) populate ;;
  inventory) inventory ;;
  verify) verify ;;
  all) backup && deploy && populate && inventory && verify ;;
  *) echo "usage: bash $0 {backup|deploy|populate|inventory|verify|all}"; exit 2 ;;
esac
