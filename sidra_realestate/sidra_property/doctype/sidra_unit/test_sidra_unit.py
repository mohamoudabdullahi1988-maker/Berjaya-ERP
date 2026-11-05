# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Unit status control (SRS v2.0 §2.3: unit status is set by services)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import (
	OTHER_COMPANY,
	SALES_MANAGER,
	SYSTEM_ONLY,
	as_user,
	ensure_base_records,
	make_scheme,
	make_unit,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Scheme", "Sidra Reservation", "Sidra Sale Contract", "Company"]


class TestSidraUnit(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.scheme = make_scheme("_TEST-UNIT")

	def test_company_comes_from_scheme(self):
		unit = make_unit(unique("_T-U"), self.scheme)
		self.assertEqual(unit.company, frappe.db.get_value("Sidra Scheme", self.scheme, "company"))
		other = make_scheme("_TEST-UNIT-OTHER", OTHER_COMPANY)
		self.assertEqual(make_unit(unique("_T-U"), other).company, OTHER_COMPANY)

	def test_new_unit_must_be_available_or_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			make_unit(unique("_T-U"), self.scheme, status="Under Contract")
		self.assertEqual(make_unit(unique("_T-U"), self.scheme, status="Blocked").status, "Blocked")

	def test_sales_manager_can_block_and_release(self):
		unit = make_unit(unique("_T-U"), self.scheme)
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc("Sidra Unit", unit.name)
			doc.status = "Blocked"
			doc.save()
			doc.status = "Available"
			doc.save()
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Available")

	def test_system_manager_is_not_a_business_approver(self):
		unit = make_unit(unique("_T-U"), self.scheme)
		with as_user(SYSTEM_ONLY), self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("Sidra Unit", unit.name)
			doc.status = "Blocked"
			doc.save()

	def test_reserved_and_contract_statuses_cannot_be_set_by_hand(self):
		unit = make_unit(unique("_T-U"), self.scheme)
		for status in ("Reserved", "Under Contract", "Sold"):
			unit.reload()
			unit.status = status
			with self.assertRaises(frappe.ValidationError):
				unit.save()

	def test_links_cannot_be_set_by_hand(self):
		unit = make_unit(unique("_T-U"), self.scheme)
		unit.current_reservation = "SRES-0000-00001"
		unit.flags.ignore_links = True
		with self.assertRaises(frappe.ValidationError):
			unit.save()
