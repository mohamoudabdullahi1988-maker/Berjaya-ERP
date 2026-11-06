# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Unit status control (SRS v2.0 §2.3: unit status is set by services)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.services.reservations import cancel_reservation, reserve_unit
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_COMPANY,
	SALES_MANAGER,
	SYSTEM_ONLY,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	make_scheme,
	make_unit,
	signing_values,
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

	# ------------------------------------------------------------ review finding 4: scheme moves
	def move(self, unit, scheme):
		doc = frappe.get_doc("Sidra Unit", unit)
		doc.scheme = scheme
		doc.save(ignore_permissions=True)
		return doc

	def test_clean_unit_can_move_to_another_company(self):
		other = make_scheme("_TEST-UNIT-OTHER", OTHER_COMPANY)
		unit = make_unit(unique("_T-U"), self.scheme)
		self.assertEqual(self.move(unit.name, other).company, OTHER_COMPANY)

	def test_cross_company_move_refused_with_price_history(self):
		other = make_scheme("_TEST-UNIT-OTHER", OTHER_COMPANY)
		unit = make_unit(unique("_T-U"), self.scheme, cash_price=5500)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.move(unit.name, other)
		self.assertIn("price history", str(caught.exception))

	def test_cross_company_move_refused_with_reservation_even_if_closed(self):
		other = make_scheme("_TEST-UNIT-OTHER", OTHER_COMPANY)
		unit = make_unit(unique("_T-U"), self.scheme)
		cancel_reservation(reserve_unit(unit.name, BUYER)["reservation"])
		with self.assertRaises(frappe.ValidationError) as caught:
			self.move(unit.name, other)
		self.assertIn("reservations", str(caught.exception))

	def test_cross_company_move_refused_with_draft_contract(self):
		ensure_contract_profiles()
		other = make_scheme("_TEST-UNIT-OTHER", OTHER_COMPANY)
		unit = make_unit(unique("_T-U"), self.scheme)
		self.draft_contract(unit.name)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.move(unit.name, other)
		self.assertIn("contracts", str(caught.exception))

	def test_any_move_refused_once_on_signed_contract(self):
		ensure_contract_profiles()
		same_company = make_scheme("_TEST-UNIT-SAME")
		unit = make_unit(unique("_T-U"), self.scheme)
		attach_signed_copy(self.draft_contract(unit.name)).submit()
		with self.assertRaises(frappe.ValidationError) as caught:
			self.move(unit.name, same_company)
		self.assertIn("signed contract", str(caught.exception))

	def test_same_company_move_allowed_with_history(self):
		same_company = make_scheme("_TEST-UNIT-SAME")
		unit = make_unit(unique("_T-U"), self.scheme, cash_price=5500)
		moved = self.move(unit.name, same_company)
		self.assertEqual((moved.scheme, moved.cash_price), (same_company, 5500))
		# the history keeps the scheme the price was set under
		self.assertEqual(frappe.db.get_value("Sidra Unit Price History", {"unit": unit.name}, "scheme"), self.scheme)

	def draft_contract(self, unit):
		return frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"contract_profile": "Profile A",
				"agreed_price": 5500,
				"units": [{"unit": unit, "allocated_price": 5500}],
				**signing_values(),
			}
		).insert(ignore_permissions=True)
