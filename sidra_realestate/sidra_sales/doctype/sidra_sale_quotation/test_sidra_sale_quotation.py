# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sale quotation (SAL-05; decision G13; docs/SALE-QUOTATION_v0.1.md)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.services.reservations import reserve_unit
from sidra_realestate.sidra_sales.doctype.sidra_sale_quotation.sidra_sale_quotation import (
	approve_discount,
	expire_quotations,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	GENERAL_MANAGER,
	OTHER_BUYER,
	OTHER_COMPANY,
	OTHER_SALES_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_held_profile,
	make_scheme,
	make_unit,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Company", "User", "Sidra Unit", "Sidra Contract Profile"]

QUOTATION = "Sidra Sale Quotation"
SCHEME = "_TEST-SQ"


class TestSidraSaleQuotation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()

	def unit(self, price=11000, **values):
		return make_unit(unique("_T-SQ"), make_scheme(SCHEME), cash_price=price, **values).name

	def quote(self, units=None, user=SALES_USER, **values):
		"""Prepared by a sales officer: (unit, cash price or None, installment price) rows."""
		units = units or [(self.unit(), None, 11000)]
		with as_user(user):
			return frappe.get_doc(
				{
					"doctype": QUOTATION,
					"customer": BUYER,
					"contract_profile": "Profile A",
					"units": [{"unit": u, "cash_price": c, "installment_price": i} for u, c, i in units],
					**values,
				}
			).insert()

	def approve(self, doc, user):
		with as_user(user):
			approve_discount(doc.name)
		doc.reload()
		return doc

	def issue(self, doc, user=SALES_USER):
		with as_user(user):
			doc = frappe.get_doc(QUOTATION, doc.name)
			doc.submit()
		return doc

	# ------------------------------------------------------------ two options side by side
	def test_profile_a_options(self):
		doc = self.quote()
		self.assertEqual((doc.company, doc.status, doc.discount_approval), (COMPANY, "Draft", "Not Needed"))
		self.assertEqual((doc.listed_total, doc.cash_total, doc.discount_amount), (11000, 11000, 0))
		self.assertEqual((doc.installment_total, doc.down_payment, doc.balance), (11000, 0, 11000))
		self.assertEqual((doc.installments, doc.due_day, doc.grace_months), (14, 5, 0))
		self.assertEqual([row.amount for row in doc.schedule], [786] * 13 + [782])  # AT-02
		self.assertEqual(getdate(doc.valid_until), getdate(add_days(today(), 7)))

	def test_installment_price_entered_and_months_adjustable(self):
		doc = self.quote([(self.unit(), None, 12000)], installments=24)
		self.assertEqual((doc.cash_total, doc.installment_total), (11000, 12000))
		self.assertEqual((len(doc.schedule), doc.schedule[0].amount), (24, 500))
		for months in (11, 37):
			with self.subTest(months=months), self.assertRaises(frappe.ValidationError):
				self.quote(installments=months)
		with self.assertRaises(frappe.ValidationError):
			self.quote([(self.unit(), None, 10999)])  # below the listed price

	def test_profile_b_down_payment_and_two_units(self):
		doc = self.quote(
			[(self.unit(11000), None, 11500), (self.unit(5500), None, 5500)], contract_profile="Profile B"
		)
		self.assertEqual((doc.listed_total, doc.installment_total), (16500, 17000))
		self.assertEqual(
			(doc.down_payment, doc.balance, doc.installments, doc.grace_months), (3000, 14000, 24, 3)
		)
		self.assertEqual(sum(row.amount for row in doc.schedule), 14000)

	def test_unit_rules(self):
		unit = self.unit()
		with self.assertRaises(frappe.ValidationError):
			self.quote([(unit, None, 11000), (unit, None, 11000)])  # twice
		with self.assertRaises(frappe.ValidationError):
			self.quote([(self.unit(price=None), 100, 100)])  # no listed price
		other = make_unit(
			unique("_T-SQ"), make_scheme("_TEST-SQ-OTHER", company=OTHER_COMPANY), cash_price=11000
		).name
		with self.assertRaises(frappe.ValidationError):
			self.quote([(unit, None, 11000), (other, None, 11000)])  # two Companies
		frappe.db.set_value("Sidra Unit", unit, "status", "Blocked")
		with self.assertRaises(frappe.ValidationError):
			self.quote([(unit, None, 11000)])

	def test_reserved_unit_only_for_its_customer(self):
		unit = self.unit()
		with as_user(SALES_USER):
			reserve_unit(unit, BUYER)
		self.assertEqual(self.quote([(unit, None, 11000)]).docstatus, 0)
		with self.assertRaises(frappe.ValidationError):
			self.quote([(unit, None, 11000)], customer=OTHER_BUYER)

	def test_held_profile_and_dates(self):
		with self.assertRaises(frappe.ValidationError):
			self.quote(contract_profile=make_held_profile().name)
		with self.assertRaises(frappe.ValidationError):
			self.quote(quotation_date=add_days(today(), 1))
		with self.assertRaises(frappe.ValidationError):
			self.quote(valid_until=add_days(today(), -1))

	# ------------------------------------------------------------ issue: offer only
	def test_issue_changes_nothing_else(self):
		doc = self.quote()
		unit = doc.units[0].unit
		contracts = frappe.db.count("Sidra Sale Contract")
		reservations = frappe.db.count("Sidra Reservation")
		doc = self.issue(doc)
		self.assertEqual((doc.docstatus, doc.status), (1, "Issued"))
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Available")  # no hold
		self.assertEqual(frappe.db.count("Sidra Sale Contract"), contracts)
		self.assertEqual(frappe.db.count("Sidra Reservation"), reservations)

	def test_listed_price_frozen_at_issue(self):
		doc = self.issue(self.quote())
		frappe.db.set_value("Sidra Unit", doc.units[0].unit, "cash_price", 12500)
		doc.reload()
		self.assertEqual((doc.units[0].listed_price, doc.cash_total), (11000, 11000))

	def test_expiry(self):
		doc = self.issue(self.quote())
		expire_quotations()
		self.assertEqual(frappe.db.get_value(QUOTATION, doc.name, "status"), "Issued")
		frappe.db.set_value(QUOTATION, doc.name, "valid_until", add_days(today(), -1))
		expire_quotations()
		self.assertEqual(frappe.db.get_value(QUOTATION, doc.name, "status"), "Expired")

	def test_who_can_prepare_and_cancel(self):
		with self.assertRaises(frappe.PermissionError):
			self.quote(user=OUTSIDER)
		with self.assertRaises(frappe.PermissionError):
			self.quote(user=GENERAL_MANAGER)
		doc = self.issue(self.quote())
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(QUOTATION, doc.name).cancel()
		with as_user(OTHER_SALES_MANAGER):
			frappe.get_doc(QUOTATION, doc.name).cancel()
		self.assertEqual(frappe.db.get_value(QUOTATION, doc.name, "status"), "Cancelled")

	# ------------------------------------------------------------ discounts (G13)
	def test_discount_up_to_five_percent_sales_manager(self):
		doc = self.quote([(self.unit(), 10450, 11000)])  # exactly 5 %
		self.assertEqual((doc.discount_amount, doc.discount_approval), (550, "Sidra Sales Manager"))
		with self.assertRaises(frappe.ValidationError):
			self.issue(doc)  # not approved yet
		with self.assertRaises(frappe.PermissionError):
			self.approve(doc, SALES_USER)  # prepared it, and not a manager
		doc = self.approve(doc, SALES_MANAGER)
		self.assertEqual(doc.discount_approved_by, SALES_MANAGER)
		self.assertEqual(self.issue(doc).status, "Issued")

	def test_discount_above_five_percent_general_manager(self):
		doc = self.quote([(self.unit(), 10449.99, 11000)])
		self.assertEqual(doc.discount_approval, "Sidra General Manager")
		with self.assertRaises(frappe.PermissionError):
			self.approve(doc, SALES_MANAGER)
		doc = self.approve(doc, GENERAL_MANAGER)
		self.assertEqual(doc.discount_approved_by, GENERAL_MANAGER)
		self.assertEqual(self.issue(doc).status, "Issued")

	def test_preparer_cannot_approve_own_discount(self):
		doc = self.quote([(self.unit(), 10900, 11000)], user=OTHER_SALES_MANAGER)
		with self.assertRaises(frappe.PermissionError):
			self.approve(doc, OTHER_SALES_MANAGER)
		self.assertEqual(self.approve(doc, SALES_MANAGER).discount_approved_by, SALES_MANAGER)

	def test_price_change_clears_approval(self):
		doc = self.approve(self.quote([(self.unit(), 10900, 11000)]), SALES_MANAGER)
		doc.notes = "Call back on Saturday"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.discount_approved_by, SALES_MANAGER)  # unrelated change keeps it
		doc.units[0].cash_price = 10800
		doc.save(ignore_permissions=True)
		self.assertIsNone(doc.discount_approved_by)
		with self.assertRaises(frappe.ValidationError):
			self.issue(doc)

	def test_listed_price_change_clears_approval(self):
		doc = self.approve(self.quote([(self.unit(), 10900, 11000)]), SALES_MANAGER)
		frappe.db.set_value("Sidra Unit", doc.units[0].unit, "cash_price", 12000)
		doc.reload()
		doc.units[0].installment_price = 12000
		doc.save(ignore_permissions=True)
		self.assertEqual((doc.discount_approval, doc.discount_approved_by), ("Sidra General Manager", None))

	def test_approval_cannot_be_forged_or_given_without_discount(self):
		doc = self.quote(
			[(self.unit(), 10900, 11000)], discount_approved_by=SALES_MANAGER, discount_approved_on=today()
		)
		self.assertIsNone(doc.discount_approved_by)
		with self.assertRaises(frappe.PermissionError):
			self.approve(self.quote(), GENERAL_MANAGER)  # nothing to approve
		with self.assertRaises(frappe.ValidationError):
			self.quote([(self.unit(), 11000.01, 11000.01)])  # cash above the listed price

	def test_print_shows_both_options(self):
		doc = self.quote([(self.unit(), None, 12000)])
		html = frappe.get_print(QUOTATION, doc.name, print_format="Sidra Sale Quotation", doc=doc)
		for text in ("sidra-logo.png", doc.name, "Cash", "Installments", "does not reserve"):
			self.assertIn(text, html)
