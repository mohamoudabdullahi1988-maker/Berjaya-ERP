# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Staff dashboard snapshot (clients/staff/docs/API-CONTRACT.md, schema_version 1)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.staff_dashboard import get_dashboard
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OUTSIDER,
	SALES_MANAGER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	make_scheme,
	make_unit,
	unique,
)


class TestStaffDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		cls.scheme = make_scheme("_TEST-DASH")

	def confirmed_contract(self):
		unit = make_unit(unique("_T-DASH"), self.scheme).name
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": "External (registered)",
				"external_reference": unique("EXT-DASH"),
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": frappe.utils.nowdate(),
				"agreed_price": 1200,
				"units": [{"unit": unit, "allocated_price": 1200}],
				"schedule": [
					{
						"row_type": "Installment",
						"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 10),
						"amount": 600,
					},
					{
						"row_type": "Installment",
						"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 45),
						"amount": 600,
					},
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
		self.assertFalse(data["sales"]["available"])
		self.assertFalse(data["jobs"]["available"])  # Sales Manager has no construction access
		self.assertTrue(all(loc["doctype"] == "Sidra Unit" for loc in data["locations"]))
		mine = [c for c in data["contracts"] if c["id"] == doc.name]
		self.assertEqual((mine[0]["status"], mine[0]["value"]), ("Confirmed", "1200.00"))
		upcoming = [r for r in data["schedule"]["upcoming"] if r["contract_id"] == doc.name]
		self.assertEqual([r["amount"] for r in upcoming], ["600.00", "600.00"])
		self.assertEqual(
			[b["label"] for b in data["schedule"]["buckets"]], ["Next 30 days", "31-60 days", "61-90 days"]
		)

	def test_company_and_period_checks(self):
		with as_user(SALES_MANAGER):
			with self.assertRaises(frappe.PermissionError):
				get_dashboard(company="_No Such Company")
			with self.assertRaises(frappe.ValidationError):
				get_dashboard(company=COMPANY, period="forever")

	def test_outsider_denied(self):
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			get_dashboard()
