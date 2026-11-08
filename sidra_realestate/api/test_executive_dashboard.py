"""Native Frappe integration: persisted synthetic records, permissions and report reconciliation."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import frappe
from frappe.desk.query_report import run as run_report
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.executive_dashboard import REPORT, executive_evidence, executive_snapshot
from sidra_realestate.api.staff_dashboard import get_dashboard
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.tests.helpers import (
	BUYER,
	GENERAL_MANAGER,
	OTHER_COMPANY,
	OUTSIDER,
	SALES_MANAGER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	ensure_company,
	ensure_user,
	make_scheme,
	make_unit,
	unique,
)

NOW = datetime(2026, 11, 8, 12, tzinfo=ZoneInfo("Africa/Mogadishu"))


class TestExecutiveDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()

	def setUp(self):
		super().setUp()
		self.company = ensure_company(unique("_Test Executive"), unique("_EX"))
		self.scheme = make_scheme(unique("_T-EXEC-S"), self.company)
		self.unit = make_unit(unique("_T-EXEC-U"), self.scheme, cash_price=250.01)

	def contract(self, **values):
		units = [make_unit(unique("_T-EXEC-CU"), self.scheme) for _ in range(2)]
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"source": "External (registered)",
				"external_reference": unique("_T-EXEC-REF"),
				"contract_type": "Installment",
				"customer": BUYER,
				"company": self.company,
				"signed_on": NOW.date(),
				"agreed_price": 1200,
				"units": [{"unit": u.name, "allocated_price": 600} for u in units],
				"schedule": [
					{"due_date": NOW.date() + timedelta(days=days), "amount": amount, "row_type": kind}
					for days, amount, kind in [
						(0, 200, "Installment"),
						(1, 200, "Installment"),
						(1, 100, "Fee"),
						(30, 200, "Installment"),
						(31, 200, "Installment"),
						(60, 300, "Installment"),
					]
				],
				**values,
			}
		).insert(ignore_permissions=True)
		return attach_signed_copy(doc).submit()

	def dashboard(self, user=GENERAL_MANAGER, **values):
		with patch("sidra_realestate.api.executive_dashboard.snapshot_time", return_value=NOW), as_user(user):
			return get_dashboard(company=self.company, **values)

	def evidence(self, cohort, user=GENERAL_MANAGER, **filters):
		with patch("sidra_realestate.api.executive_dashboard.snapshot_time", return_value=NOW), as_user(user):
			return executive_evidence(
				{
					"company": self.company,
					"metric": cohort,
					"period": "this_month",
					"as_of": str(NOW.date()),
					**filters,
				}
			)

	def test_saved_sources_reconcile_without_join_fanout(self):
		doc = self.contract()
		data = self.dashboard()
		self.assertEqual(data["currency"], "USD")
		self.assertTrue(data["scope"]["company_name"])
		metrics = data["executive"]["metrics"]
		self.assertEqual(metrics["sales_value"]["value"], "1200.00")
		self.assertEqual(metrics["available_units"]["value"], 1)
		self.assertEqual(metrics["available_units"]["asking_value"], "250.01")
		self.assertEqual(metrics["due_next_30_days"]["value"], "500.00")
		self.assertEqual(metrics["due_next_30_days"]["basis"], "gross_schedule")
		rows = self.evidence("scheduled_dues")
		self.assertEqual(len(rows), 3)
		self.assertEqual(len({r["row_reference"] for r in rows}), 3)
		self.assertTrue(all(r["record"] == doc.name for r in rows))
		self.assertEqual(sum(Decimal(r["value"]) for r in rows), Decimal("500.00"))
		self.assertEqual(len(self.evidence("sales_value")), 1)
		self.assertEqual(data["as_of"], NOW.isoformat(timespec="seconds"))
		self.assertEqual(data["executive"]["trends"]["months"][-1]["sales_value"], "1200.00")
		filters = {
			key: value[0]
			for key, value in parse_qs(urlparse(metrics["sales_value"]["drilldown"]["path"]).query).items()
		}
		with (
			patch("sidra_realestate.api.executive_dashboard.snapshot_time", return_value=NOW),
			as_user(GENERAL_MANAGER),
		):
			result = run_report(REPORT, filters=filters, ignore_prepared_report=True)
		self.assertEqual(sum(Decimal(str(r["value"])) for r in result["result"]), Decimal("1200.00"))

	def test_missing_finance_targets_and_baseline_are_not_zero_or_invented(self):
		metrics = self.dashboard()["executive"]["metrics"]
		for key in ("cash_collected", "overdue_balance", "projects_on_schedule"):
			self.assertFalse(metrics[key]["available"])
			self.assertNotIn("value", metrics[key])
		self.assertIsNone(metrics["sales_value"]["target"])
		self.assertEqual(metrics["sales_value"]["value"], "0.00")
		self.assertEqual(metrics["due_next_30_days"]["value"], "0.00")
		self.assertFalse(metrics["due_next_30_days"]["expected_receipts"]["available"])
		self.unit.db_set("cash_price", 0)
		self.assertIsNone(self.dashboard()["executive"]["metrics"]["available_units"]["asking_value"])

	def test_period_end_currency_and_inconsistent_links_are_excluded(self):
		doc = self.contract()
		doc.db_set("signed_on", NOW.date() + timedelta(days=1))
		self.assertEqual(self.dashboard()["executive"]["metrics"]["sales_value"]["value"], "0.00")
		doc.db_set("signed_on", NOW.date())
		doc.db_set("currency", "EUR")
		self.assertEqual(self.dashboard()["executive"]["metrics"]["sales_value"]["value"], "0.00")
		self.assertEqual(self.dashboard()["schedule"]["upcoming"], [])
		doc.db_set("currency", "USD")
		frappe.db.set_value("Sidra Unit", doc.units[0].unit, "scheme", "_Missing Executive Scheme")
		self.assertEqual(self.dashboard()["executive"]["metrics"]["sales_value"]["value"], "0.00")
		self.assertEqual(self.evidence("scheduled_dues"), [])

	def test_management_role_and_direct_report_access(self):
		self.contract()
		self.assertFalse(self.dashboard(SALES_MANAGER)["executive"]["available"])
		for user in (SALES_MANAGER, OUTSIDER):
			with self.assertRaises(frappe.PermissionError):
				self.evidence("sales_value", user)
		with self.assertRaises(frappe.AuthenticationError):
			self.evidence("sales_value", "Guest")
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			run_report(REPORT, filters={"company": self.company, "metric": "sales_value"})

	def test_company_user_permission_and_tampered_filters(self):
		other_scheme = make_scheme(unique("_T-EXEC-OTHER"), OTHER_COMPANY)
		make_unit(unique("_T-EXEC-OTHER-U"), other_scheme)
		user = ensure_user(unique("exec").lower() + "@example.com", ["Sidra General Manager"])
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": self.company,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user)
		with self.assertRaises(frappe.PermissionError):
			self.evidence("available_units", user, company=OTHER_COMPANY)
		self.assertEqual(len(self.evidence("available_units", user)), 1)
		for filters in (
			{"period": "forever"},
			{"metric": "cash_collected"},
			{"project": "not-authorized"},
			{"as_of": "2026-11-07"},
			{"metric": ["sales_value"]},
			{"company": {"name": self.company}},
		):
			with self.assertRaises(frappe.ValidationError):
				self.evidence("sales_value", **filters)
		with self.assertRaises(frappe.ValidationError):
			self.dashboard(project="not-authorized")

	def test_recorded_stage_exceptions_have_real_source_and_no_financial_impact(self):
		job = frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"company": self.company,
				"customer": BUYER,
				"service_type": "Full Construction",
				"status": "In Progress",
				"engineer": GENERAL_MANAGER,
				"stages": [
					{"stage_name": "Recorded late stage", "planned_end": "2026-11-06", "completion_pct": 20},
					{"stage_name": "No dates", "completion_pct": 0},
				],
			}
		).insert(ignore_permissions=True)
		before = frappe.db.get_value(job.doctype, job.name, "modified")
		data = self.dashboard()["executive"]
		self.assertEqual(data["decisions"]["total"], 1)
		item = data["decisions"]["items"][0]
		self.assertEqual(item["reference"], job.name)
		self.assertEqual(item["due_date"], "2026-11-06")
		self.assertEqual(item["owner"], GENERAL_MANAGER)
		self.assertNotIn("amount", item["impact"])
		self.assertEqual(frappe.db.get_value(job.doctype, job.name, "modified"), before)
		self.assertEqual(len(self.evidence("stage_exceptions")), 1)

	def test_receipt_and_contract_records_are_not_modified(self):
		doc = self.contract()
		before = frappe.db.get_value(
			doc.doctype, doc.name, ["modified", "agreed_price", "terms_snapshot"], as_dict=True
		)
		vouchers = frappe.db.count("Payment Entry")
		self.dashboard()
		self.evidence("sales_value")
		self.assertEqual(
			before,
			frappe.db.get_value(
				doc.doctype, doc.name, ["modified", "agreed_price", "terms_snapshot"], as_dict=True
			),
		)
		self.assertEqual(frappe.db.count("Payment Entry"), vouchers)

	def test_unit_user_permission_excludes_whole_contract_not_a_partial_value(self):
		self.contract()
		user = ensure_user(unique("execunit").lower() + "@example.com", ["Sidra General Manager"])
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Sidra Unit",
				"for_value": self.unit.name,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user)
		self.assertEqual(self.evidence("sales_value", user), [])
		self.assertEqual(self.evidence("scheduled_dues", user), [])
		self.assertEqual([r["record"] for r in self.evidence("available_units", user)], [self.unit.name])

	def test_unreadable_exception_sources_do_not_claim_no_escalations(self):
		from sidra_realestate.api.executive_dashboard import _read

		def permitted_read(doctype, *args, **kwargs):
			return (
				None
				if doctype in {"Sidra Construction Job", "Sidra Reservation"}
				else _read(doctype, *args, **kwargs)
			)

		with (
			as_user(GENERAL_MANAGER),
			patch("sidra_realestate.api.executive_dashboard._read", side_effect=permitted_read),
		):
			data = executive_snapshot(self.company, "USD", "this_month", NOW)
		self.assertFalse(data["decisions"]["available"])
		self.assertNotIn("total", data["decisions"])

	def test_native_report_escapes_recorded_stage_text(self):
		job = frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"company": self.company,
				"customer": BUYER,
				"service_type": "Full Construction",
				"status": "In Progress",
				"stages": [
					{
						"stage_name": "Recorded legacy stage",
						"planned_end": "2026-11-06",
						"completion_pct": 0,
					}
				],
			}
		).insert(ignore_permissions=True)
		# Simulate a legacy/imported stored value without weakening normal input sanitization.
		frappe.db.set_value(
			"Sidra Project Stage", job.stages[0].name, "stage_name", "<img src=x onerror=alert(1)>"
		)
		with (
			patch("sidra_realestate.api.executive_dashboard.snapshot_time", return_value=NOW),
			as_user(GENERAL_MANAGER),
		):
			data = run_report(
				REPORT,
				filters={"company": self.company, "metric": "stage_exceptions"},
				ignore_prepared_report=True,
			)
		self.assertEqual(len(data["result"]), 1)
		self.assertIn("&lt;img", data["result"][0]["note"])
		self.assertNotIn("<img", data["result"][0]["note"])
