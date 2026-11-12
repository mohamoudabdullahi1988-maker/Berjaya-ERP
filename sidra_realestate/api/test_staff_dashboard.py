# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Staff dashboard snapshot (clients/staff/docs/API-CONTRACT.md, schema_version 1)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.executive_dashboard import snapshot_time
from sidra_realestate.api.staff_dashboard import get_dashboard
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	GENERAL_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	ensure_user,
	make_scheme,
	make_unit,
	unique,
)

PROJECT_MANAGER = "sidra.projects@example.com"
INSPECTOR = "sidra.inspector@example.com"


class TestStaffDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		cls.scheme = make_scheme("_TEST-DASH")
		ensure_user(PROJECT_MANAGER, ["Sidra Project Manager"])
		ensure_user(INSPECTOR, ["Sidra Inspector"])
		frappe.db.commit()

	def confirmed_contract(self, schedule=None):
		today = snapshot_time().date()  # Dashboard dates use Mogadishu, not the site's calendar.
		unit = make_unit(unique("_T-DASH"), self.scheme).name
		if schedule is None:
			schedule = [(10, 600), (45, 600)]
		price = round(sum(amount for _days, amount in schedule), 2)
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": "External (registered)",
				"external_reference": unique("EXT-DASH"),
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": today,
				"agreed_price": price,
				"units": [{"unit": unit, "allocated_price": price}],
				"schedule": [
					{
						"row_type": "Installment",
						"due_date": frappe.utils.add_days(today, days),
						"amount": amount,
					}
					for days, amount in schedule
				],
			}
		).insert(ignore_permissions=True)
		attach_signed_copy(doc).submit()
		return doc

	def test_payload_shape_and_values(self):
		doc = self.confirmed_contract()
		with as_user(SALES_MANAGER):
			data = get_dashboard(company=COMPANY, period="this_month")
		self.assertEqual(data["schema_version"], 1)
		self.assertEqual(data["scope"]["company_id"], COMPANY)
		self.assertIn(COMPANY, [c["id"] for c in data["companies"]])
		for key in ("summary", "property", "schedule", "contracts", "locations", "sales", "payments", "jobs"):
			self.assertIn(key, data)
		self.assertIsInstance(data["summary"]["agreed_contract_value"], str)
		self.assertGreaterEqual(data["summary"]["confirmed_contracts"], 1)
		self.assertFalse(data["payments"]["available"])  # never zero receipts
		self.assertTrue(data["payments"]["reason"])
		if data["sales"]["available"]:
			self.assertIsNone(data["sales"]["conversion_rate"])
			self.assertIsNone(data["sales"]["qualified_opportunities"])
		self.assertFalse(data["jobs"]["available"])  # Sales Manager has no construction access
		self.assertTrue(all(loc["doctype"] == "Sidra Unit" for loc in data["locations"]))
		mine = [c for c in data["contracts"] if c["id"] == doc.name]
		self.assertEqual((mine[0]["status"], mine[0]["value"]), ("Confirmed", "1200.00"))
		upcoming = [r for r in data["schedule"]["upcoming"] if r["contract_id"] == doc.name]
		self.assertEqual([r["amount"] for r in upcoming], ["600.00", "600.00"])
		self.assertEqual(
			[b["label"] for b in data["schedule"]["buckets"]],
			["Due today", "Next 30 days", "31-60 days", "61-90 days"],
		)
		self.assertTrue(data["schedule"]["available"])

	def test_company_and_period_checks(self):
		with as_user(SALES_MANAGER):
			with self.assertRaises(frappe.PermissionError):
				get_dashboard(company="_No Such Company")
			with self.assertRaises(frappe.ValidationError):
				get_dashboard(company=COMPANY, period="forever")

	def test_outsider_denied(self):
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			get_dashboard()

	def construction_job(self, status, stages):
		return frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"company": COMPANY,
				"customer": BUYER,
				"service_type": "Full Construction",
				"status": status,
				"stages": stages,
			}
		).insert(ignore_permissions=True)

	def test_construction_roles_get_their_view_without_sales_access(self):
		self.construction_job("In Progress", [{"stage_name": "Foundation", "completion_pct": 10}])
		for user in (PROJECT_MANAGER, INSPECTOR):
			with as_user(user):
				data = get_dashboard(company=COMPANY)
			self.assertTrue(data["jobs"]["available"], user)
			# record types the role cannot read are unknown, never zero and never an error
			for key in ("units_available", "confirmed_contracts", "agreed_contract_value"):
				self.assertIsNone(data["summary"][key], (user, key))
			self.assertIsNone(data["property"]["total"])
			self.assertEqual(data["property"]["counts"], [])
			self.assertEqual(data["contracts"], [])
			self.assertFalse(data["schedule"]["available"])
			self.assertEqual((data["schedule"]["buckets"], data["schedule"]["upcoming"]), ([], []))
			self.assertTrue(all(loc["doctype"] == "Sidra Construction Job" for loc in data["locations"]))
			self.assertFalse(data["executive"]["available"])

	def test_schedule_buckets_share_the_executive_next_30_day_window(self):
		before = self.bucket_amounts()
		self.confirmed_contract(schedule=[(0, 100.10), (1, 200.20), (30, 300.30), (31, 0.40)])
		after = self.bucket_amounts()
		delta = {label: after[label] - before.get(label, 0) for label in after}
		# today is its own bucket; "Next 30 days" is tomorrow through day 30, as in the executive view
		self.assertEqual(str(delta["Due today"]), "100.10")
		self.assertEqual(str(delta["Next 30 days"]), "500.50")
		self.assertEqual(str(delta["31-60 days"]), "0.40")

	def bucket_amounts(self):
		from decimal import Decimal

		with as_user(SALES_MANAGER):
			buckets = get_dashboard(company=COMPANY)["schedule"]["buckets"]
		return {b["label"]: Decimal(b["amount"]) for b in buckets}

	def test_overdue_milestones_follow_the_shared_stage_rule(self):
		with as_user(GENERAL_MANAGER):
			before = get_dashboard(company=COMPANY)["jobs"].get("overdue_milestones") or 0
		past = frappe.utils.add_days(snapshot_time().date(), -3)
		self.construction_job(
			"In Progress",
			[
				{"stage_name": "Late, incomplete", "planned_end": past, "completion_pct": 40},
				{"stage_name": "Late, at 100%", "planned_end": past, "completion_pct": 100},
				{"stage_name": "Finished late", "planned_end": past, "actual_end": past, "completion_pct": 100},
			],
		)
		self.construction_job(
			"Cancelled", [{"stage_name": "Cancelled job stage", "planned_end": past, "completion_pct": 0}]
		)
		with as_user(GENERAL_MANAGER):
			jobs = get_dashboard(company=COMPANY)["jobs"]
		self.assertEqual(jobs["overdue_milestones"] - before, 1)

	def test_recorded_sales_activity_is_company_scoped(self):
		from sidra_realestate.services.sales_activity import sales_activity

		today = snapshot_time().date()
		with as_user("Administrator"):
			before = sales_activity(COMPANY, today, today)
			frappe.get_doc({
				"doctype": "Lead", "first_name": unique("_TEST-ACTIVITY"),
				"company": COMPANY, "status": "Lead",
			}).insert()
			after = sales_activity(COMPANY, today, today)
		self.assertEqual(after["basis"], "recorded_lead_status")
		before_count = sum(row["value"] for row in before["pipeline"])
		self.assertEqual(sum(row["value"] for row in after["pipeline"]), before_count + 1)
		self.assertIsNone(after["conversion_rate"])
		self.assertIsNone(after["qualified_opportunities"])
		with as_user(PROJECT_MANAGER):
			self.assertFalse(sales_activity(COMPANY, today, today)["available"])
