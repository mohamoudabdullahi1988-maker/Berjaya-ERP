"""Run the checker's embedded Python without a live site or financial writes."""

import contextlib
import copy
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "sidra-pilot-check.sh"
SOURCE = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
COUNTS = {"Sales Invoice": 60, "Purchase Invoice": 35, "Payment Entry": 64, "Journal Entry": 1}


class TestPilotCheck(unittest.TestCase):
    def run_check(self, change=None, refusal=None):
        result = {"company": "Sidra Homes", "expected": dict(COUNTS), "posted": dict(COUNTS)}
        manifest = {"from_date": "2025-11-13", "as_of": "2026-11-13"}
        if change:
            change(result, manifest)
        frappe = types.ModuleType("frappe")
        for name in ("init", "connect", "destroy"):
            setattr(frappe, name, Mock())
        frappe.db = types.SimpleNamespace(rollback=Mock())
        pilot = types.ModuleType("sidra_realestate.pilot_demo")
        pilot.MANIFEST, pilot.SCHEMA = "sidra-pilot-demo-v1.json", 1
        pilot.verify_pilot_demo = Mock(return_value=copy.deepcopy(result), side_effect=refusal)
        pilot._read_manifest = Mock(return_value=manifest)
        # Neither loader is exposed: accidentally invoking one must fail the check.
        package = types.ModuleType("sidra_realestate")
        package.__path__ = []
        modules = {"frappe": frappe, "sidra_realestate": package, "sidra_realestate.pilot_demo": pilot}
        out, err = io.StringIO(), io.StringIO()
        status = 0
        with patch.dict(sys.modules, modules), patch.object(sys, "argv", ["-", "/test/bench"]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    exec(compile(SOURCE, str(SCRIPT), "exec"), {})
                except SystemExit as exc:
                    status = exc.code
        frappe.db.rollback.assert_called_once_with()
        frappe.destroy.assert_called_once_with()
        pilot.verify_pilot_demo.assert_called_once_with()
        return status, out.getvalue(), err.getvalue()

    def test_verified_pilot_prints_reporting_dates_and_limits(self):
        status, out, err = self.run_check()
        self.assertEqual(status, 0)
        self.assertEqual(err, "")
        self.assertIn("Total submitted vouchers: 160", out)
        self.assertIn("2025-11-13 through 2026-11-13", out)
        self.assertIn("NOT VERIFIED: ledger amounts", out)

    def test_missing_voucher_is_a_failure_even_if_verifier_returns_normally(self):
        status, out, err = self.run_check(lambda r, m: r["posted"].update({"Payment Entry": 63}))
        self.assertEqual(status, 1)
        self.assertNotIn("PASS:", out)
        self.assertIn("Payment Entry: posted=63, expected=64", err)

    def test_guard_refusal_retains_original_exception(self):
        status, out, err = self.run_check(refusal=RuntimeError("Refusing: foreign ledger activity"))
        self.assertEqual(status, 1)
        self.assertNotIn("PASS:", out)
        self.assertIn("RuntimeError: Refusing: foreign ledger activity", err)
        self.assertNotIn("NameError", err)

    def test_incomplete_counts_cannot_pass(self):
        status, out, err = self.run_check(lambda r, m: r["posted"].pop("Journal Entry"))
        self.assertEqual(status, 1)
        self.assertNotIn("PASS:", out)
        self.assertIn("Incomplete voucher counts", err)

    def test_wrong_company_cannot_pass(self):
        status, out, err = self.run_check(lambda r, m: r.update(company="Other Company"))
        self.assertEqual(status, 1)
        self.assertNotIn("PASS:", out)
        self.assertIn("Unexpected Company", err)

    def test_invalid_manifest_period_cannot_pass(self):
        status, out, err = self.run_check(lambda r, m: m.update(from_date="2027-01-01"))
        self.assertEqual(status, 1)
        self.assertNotIn("PASS:", out)
        self.assertIn("Invalid reporting dates", err)


if __name__ == "__main__":
    unittest.main()
