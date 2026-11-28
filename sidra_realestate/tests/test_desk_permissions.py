# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""G44: who opens the native ERPNext records in Desk; Selling holds only the copies of Sidra records."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.services.desk_permissions import ensure_desk_permissions
from sidra_realestate.services.erpnext_selling import ensure_selling_setup
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	INSPECTOR,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	ensure_user,
)

FINANCE = "sidra.finance@example.com"
GM_ONLY = "sidra.gm.only@example.com"  # the GM role without the profile's Sales User
PM_ONLY = "sidra.pm.only@example.com"  # the PM role without the profile's Projects User


def can(user, doctype, right="read"):
	return bool(frappe.has_permission(doctype, right, user=user))


class TestDeskPermissions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_user(FINANCE, ["Sidra Finance Reviewer"])
		ensure_user(GM_ONLY, ["Sidra General Manager"])
		ensure_user(PM_ONLY, ["Sidra Project Manager"])
		ensure_selling_setup()
		ensure_desk_permissions()

	def test_finance_reads_sales_projects_and_assets_only(self):
		for doctype in ("Quotation", "Sales Order", "Project", "Task", "Asset"):
			with self.subTest(doctype=doctype):
				self.assertTrue(can(FINANCE, doctype))
				self.assertFalse(can(FINANCE, doctype, "write"))
				self.assertFalse(can(FINANCE, doctype, "create"))

	def test_assets_register_for_finance_gm_and_project_staff(self):
		for user in (FINANCE, GM_ONLY, PM_ONLY):
			with self.subTest(user=user):
				self.assertTrue(can(user, "Asset"))
				self.assertTrue(can(user, "Asset Category"))
				self.assertFalse(can(user, "Asset", "create"))
		self.assertFalse(can(SALES_USER, "Asset"))

	def test_project_staff_raise_material_requests(self):
		for right in ("read", "create", "submit"):
			self.assertTrue(can(PM_ONLY, "Material Request", right))
		self.assertTrue(can(PM_ONLY, "Warehouse"))
		self.assertTrue(can(PM_ONLY, "Item"))
		self.assertFalse(can(INSPECTOR, "Material Request", "create"))

	def test_erpnext_rules_are_kept(self):
		self.assertTrue(can(SALES_USER, "Sales Order", "write"))  # Sales User
		self.assertTrue(can(PROJECT_MANAGER, "Project", "write"))  # Projects User
		self.assertTrue(can("Administrator", "Asset", "create"))

	def test_running_again_changes_nothing(self):
		before = frappe.db.count("Custom DocPerm")
		ensure_desk_permissions()
		self.assertEqual(frappe.db.count("Custom DocPerm"), before)

	def test_quotations_and_sales_orders_only_as_copies(self):
		for doctype, extra in (
			("Quotation", {"quotation_to": "Customer", "party_name": BUYER}),
			("Sales Order", {"customer": BUYER, "delivery_date": frappe.utils.today()}),
		):
			doc = frappe.get_doc(
				{
					"doctype": doctype,
					"company": COMPANY,
					"transaction_date": frappe.utils.today(),
					"items": [{"item_code": "Land plot sale", "qty": 1, "rate": 1}],
					**extra,
				}
			)
			for user in (SALES_MANAGER, "Administrator"):
				with self.subTest(doctype=doctype, user=user), as_user(user):
					with self.assertRaisesRegex(frappe.PermissionError, "Sidra records"):
						doc.insert(ignore_permissions=True)
