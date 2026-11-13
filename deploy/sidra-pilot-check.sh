#!/usr/bin/env bash
# Verify an existing pilot dataset. Never loads, repairs or deletes records.
# Run as root or frappe on the Sidra test VPS. Version 0.1, 13 Nov 2026.
set -Eeuo pipefail

if [[ ${1:-} == --help ]]; then
  echo "Usage: bash sidra-pilot-check.sh"
  echo "Read-only pilot verification for sidra.local / Sidra Homes."
  exit 0
fi
if (( $# )); then
  echo "Usage: bash sidra-pilot-check.sh" >&2
  exit 2
fi

BENCH=${SIDRA_BENCH:-/home/frappe/sidra/frappe-bench}
[[ -x "$BENCH/env/bin/python" && -d "$BENCH/sites/sidra.local" ]] || {
  echo "STOPPED: bench Python or site sidra.local is missing under $BENCH." >&2
  exit 1
}

runner=()
if (( EUID == 0 )); then
  runner=(sudo -u frappe -H --)
elif [[ $(id -un) != frappe ]]; then
  echo "STOPPED: run as root or the frappe bench operator." >&2
  exit 1
fi

cd "$BENCH"
"${runner[@]}" "$BENCH/env/bin/python" - "$BENCH" <<'PY'
import sys
import traceback
from datetime import date
from pathlib import Path

import frappe

try:
    bench = Path(sys.argv[1]).resolve()
    frappe.init(site="sidra.local", sites_path=str(bench / "sites"))
    frappe.connect()

    # Calling Python directly preserves the original exception: bench execute
    # can mask a guard refusal with its eval fallback's NameError.
    from sidra_realestate.pilot_demo import MANIFEST, SCHEMA, _read_manifest, verify_pilot_demo

    result = verify_pilot_demo()
    if result.get("company") != "Sidra Homes":
        raise ValueError("Unexpected Company returned by the pilot verifier.")

    expected = result["expected"]
    posted = result["posted"]
    types = {"Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"}
    if set(expected) != types or set(posted) != types:
        raise ValueError("Incomplete voucher counts returned by the pilot verifier.")
    for doctype in sorted(types):
        want, have = expected[doctype], posted[doctype]
        if type(want) is not int or type(have) is not int or want < 0 or have != want:
            raise ValueError(f"{doctype}: posted={have!r}, expected={want!r}.")

    manifest = _read_manifest(MANIFEST, SCHEMA)
    start = date.fromisoformat(manifest["from_date"])
    end = date.fromisoformat(manifest["as_of"])
    if start > end:
        raise ValueError("Invalid reporting dates in the pilot manifest.")

    print("Company: Sidra Homes | Site: sidra.local")
    print("PASS: existing pilot ownership checks and submitted voucher counts")
    for doctype in sorted(types):
        print(f"  {doctype}: posted={posted[doctype]}, expected={expected[doctype]}")
    print(f"  Total submitted vouchers: {sum(posted.values())}")
    print(f"Report period: {start} through {end}")
    print("Open /sidra and select Sidra Homes in each native financial report.")
    print("NOT VERIFIED: ledger amounts, current operational counts and browser screens.")
    print("Finished. No loader was run and no records were changed.")
except Exception:
    print("STOPPED: verification failed. Original error follows; do not rerun a loader.", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        if frappe.db:
            frappe.db.rollback()
    finally:
        frappe.destroy()
PY
