# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sale contract (SAL-13, INS-02, INS-14, INS-20; SRS v2.0 §2.3, §3.3; handoff v2.0 first-PR checklist)."""

import json
from datetime import date

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.services.reservations import reserve_unit
from sidra_realestate.services.units import UnitNotAvailable
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_BUYER,
	OTHER_COMPANY,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	make_held_profile,
	make_scheme,
	make_unit,
	signing_values,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Customer", "Company", "Sidra Contract Profile", "User"]

LEDGER_DOCTYPES = ("GL Entry", "Payment Ledger Entry", "Sales Invoice", "Payment Entry", "Journal Entry")


class TestSidraSaleContract(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		cls.scheme = make_scheme("_TEST-SSC")
		cls.other_scheme = make_scheme("_TEST-SSC-OTHER", OTHER_COMPANY)

	def unit(self, scheme=None):
		return make_unit(unique("_T-SSC"), scheme or self.scheme).name

	def contract(self, units, *, profile="Profile A", signed_on="2026-11-05", customer=BUYER, **values):
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"customer": customer,
				"company": COMPANY,
				"signed_on": signed_on,
				"contract_profile": profile,
				"agreed_price": sum(price for _, price in units),
				"units": [{"unit": unit, "allocated_price": price} for unit, price in units],
				**signing_values(),
				**values,
			}
		)
		doc.insert(ignore_permissions=True)
		return attach_signed_copy(doc)

	# ------------------------------------------------------------ schedules
	def test_hagbad_two_plots_profile_a(self):
		"""Checklist: Profile A, two plots, $11,000 -> 13 x $786 + $782 (AT-02)."""
		u1, u2 = self.unit(), self.unit()
		doc = self.contract([(u1, 5500), (u2, 5500)])
		self.assertEqual(doc.schedule, [])  # nothing before submit
		doc.submit()

		amounts = [row.amount for row in doc.schedule]
		self.assertEqual(amounts, [786] * 13 + [782])
		self.assertEqual(sum(amounts), 11000)
		self.assertEqual([row.seq for row in doc.schedule], list(range(1, 15)))
		self.assertEqual(getdate(doc.schedule[0].due_date), date(2026, 12, 5))
		self.assertEqual(getdate(doc.schedule[-1].due_date), date(2028, 1, 5))
		self.assertEqual((doc.down_payment, doc.balance, doc.installments, doc.due_day), (0, 11000, 14, 5))
		for unit in (u1, u2):
			self.assertEqual(
				frappe.db.get_value("Sidra Unit", unit, ["status", "current_contract"]),
				("Under Contract", doc.name),
			)

	def test_at01_dates(self):
		doc = self.contract([(self.unit(), 14000)], signed_on="2025-08-31")
		doc.submit()
		self.assertEqual({row.amount for row in doc.schedule}, {1000})
		self.assertEqual(getdate(doc.schedule[0].due_date), date(2025, 9, 5))
		self.assertEqual(getdate(doc.schedule[-1].due_date), date(2026, 10, 5))

	# ------------------------------------------------------------ Profile B (D4) and legal hold
	def test_profile_b_submits_after_d4(self):
		"""D4 (issue #13): Profile B has no hold; AT-03 terms, 24 x $250 from the 10th after 3 months' grace."""
		unit = self.unit()
		doc = self.contract([(unit, 9000)], profile="Profile B", signed_on="2026-01-15")
		doc.submit()
		self.assertEqual((doc.down_payment, doc.balance, doc.installments, doc.grace_months), (3000, 6000, 24, 3))
		self.assertEqual(json.loads(doc.terms_snapshot)["title_deadline_days"], 20)
		self.assertEqual([row.amount for row in doc.schedule], [250] * 24)
		self.assertEqual(getdate(doc.schedule[0].due_date), date(2026, 4, 10))
		self.assertEqual(getdate(doc.schedule[-1].due_date), date(2028, 3, 10))
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")

	def test_held_profile_draft_allowed_but_submit_blocked(self):
		unit = self.unit()
		doc = self.contract([(unit, 9000)], profile=make_held_profile().name, signed_on="2026-01-15")
		self.assertEqual((doc.down_payment, doc.balance, doc.installments, doc.grace_months), (3000, 6000, 24, 3))

		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		self.assertIn("legal hold", str(caught.exception))
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Available")
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 0)

	# ------------------------------------------------------------ frozen terms
	def test_at12_profile_edit_does_not_reach_saved_contract(self):
		doc = self.contract([(self.unit(), 14000)], signed_on="2025-08-31")
		profile = frappe.get_doc("Sidra Contract Profile", "Profile A")
		profile.installments = 20
		profile.save(ignore_permissions=True)
		self.addCleanup(frappe.db.set_value, "Sidra Contract Profile", "Profile A", "installments", 14)

		doc.reload()
		doc.submit()
		self.assertEqual(json.loads(doc.terms_snapshot)["installments"], 14)
		self.assertEqual(len(doc.schedule), 14)

	def test_collection_rules_frozen_with_terms(self):
		"""Issue #3: the profile's collections rules are frozen into the contract like other terms."""
		self.addCleanup(
			frappe.db.set_value, "Sidra Contract Profile", "Profile A", "penalty_cap_basis", "Per Installment"
		)
		frappe.db.set_value("Sidra Contract Profile", "Profile A", "penalty_cap_basis", "Per Calendar Month")
		doc = self.contract([(self.unit(), 14000)], signed_on="2025-08-31")
		frappe.db.set_value("Sidra Contract Profile", "Profile A", "penalty_cap_basis", "Per Installment")

		doc.reload()
		doc.submit()
		snapshot = json.loads(doc.terms_snapshot)
		self.assertEqual(snapshot["penalty_cap_basis"], "Per Calendar Month")
		self.assertEqual(doc.penalty_cap_basis, "Per Calendar Month")
		self.assertEqual(snapshot["notice_last_day"], "Counts as Late")
		self.assertEqual(snapshot["title_part_month"], "Pending Decision")

	def test_profile_and_snapshot_locked_after_draft_save(self):
		doc = self.contract([(self.unit(), 14000)])
		doc.contract_profile = "Profile B"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

		doc.reload()
		terms = json.loads(doc.terms_snapshot)
		terms["installments"] = 7
		doc.terms_snapshot = json.dumps(terms)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_markup_profile_not_supported_in_p0(self):
		name = unique("_Test Markup")
		frappe.get_doc(
			{
				"doctype": "Sidra Contract Profile",
				"profile_name": name,
				"installments": 12,
				"due_day": 5,
				"markup_rate": 10,
				"title_deadline_days": 20,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.contract([(self.unit(), 12000)], profile=name)

	def test_retired_profile_rejected(self):
		name = unique("_Test Retired")
		frappe.get_doc(
			{
				"doctype": "Sidra Contract Profile",
				"profile_name": name,
				"installments": 12,
				"due_day": 5,
				"title_deadline_days": 20,
				"active": 0,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.contract([(self.unit(), 12000)], profile=name)

	# ------------------------------------------------------------ invariants
	def test_unit_prices_must_add_up(self):
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"contract_profile": "Profile A",
				"agreed_price": 11000,
				"units": [{"unit": self.unit(), "allocated_price": 5500}, {"unit": self.unit(), "allocated_price": 5000}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_duplicate_units_rejected(self):
		unit = self.unit()
		with self.assertRaises(frappe.ValidationError):
			self.contract([(unit, 5500), (unit, 5500)])

	def test_unit_from_another_company_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.contract([(self.unit(self.other_scheme), 5500)])

	def test_notary_reference_format(self):
		with self.assertRaises(frappe.ValidationError):
			self.contract([(self.unit(), 5500)], notary_reference="IPN-123")
		self.assertTrue(self.contract([(self.unit(), 5500)], notary_reference="IPN/HL/042/1999"))

	# ------------------------------------------------------------ reservations
	def test_unit_reserved_for_another_customer_rejected(self):
		unit = self.unit()
		reserve_unit(unit, OTHER_BUYER)
		with self.assertRaises(UnitNotAvailable):
			self.contract([(unit, 5500)])

	def test_reservation_converted_on_submit(self):
		unit = self.unit()
		reservation = reserve_unit(unit, BUYER)["reservation"]
		doc = self.contract([(unit, 5500)])
		doc.submit()
		self.assertEqual(
			frappe.db.get_value("Sidra Reservation", reservation, ["status", "sale_contract"]),
			("Converted", doc.name),
		)
		self.assertIsNone(frappe.db.get_value("Sidra Unit", unit, "current_reservation"))

	def test_unit_under_contract_cannot_be_sold_again(self):
		unit = self.unit()
		self.contract([(unit, 5500)]).submit()
		with self.assertRaises(UnitNotAvailable):
			self.contract([(unit, 5500)], customer=OTHER_BUYER)

	def test_two_drafts_for_one_unit_only_first_submits(self):
		unit = self.unit()
		first = self.contract([(unit, 5500)])
		second = self.contract([(unit, 5500)])
		first.submit()
		with self.assertRaises(UnitNotAvailable):
			second.submit()

	# ------------------------------------------------------------ side effects
	def test_submit_creates_no_accounting_or_ownership_records(self):
		before = {dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}
		self.contract([(self.unit(), 11000)]).submit()
		self.assertEqual({dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}, before)

	def test_cancel_refused_and_unit_stays_protected(self):
		unit = self.unit()
		doc = self.contract([(unit, 5500)])
		doc.submit()
		with self.assertRaises(frappe.ValidationError):
			doc.cancel()
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")

	def test_cash_contract_at_month_end(self):
		"""Checklist: a cash contract dated 29/30/31 submits without a due-date rollover (issue #1)."""
		for day in ("2026-01-29", "2026-01-30", "2026-01-31"):
			doc = frappe.get_doc(
				{
					"doctype": "Sidra Sale Contract",
					"contract_type": "Cash",
					"customer": BUYER,
					"company": COMPANY,
					"signed_on": day,
					"agreed_price": 5500,
					"units": [{"unit": self.unit(), "allocated_price": 5500}],
					**signing_values(),
				}
			).insert(ignore_permissions=True)
			attach_signed_copy(doc).submit()
			self.assertEqual(doc.schedule, [])
			self.assertEqual((doc.down_payment, doc.balance, doc.installments), (0, 0, 0))

	def test_cash_contract_takes_no_profile(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Sidra Sale Contract",
					"contract_type": "Cash",
					"customer": BUYER,
					"company": COMPANY,
					"signed_on": "2026-11-05",
					"contract_profile": "Profile A",
					"agreed_price": 5500,
					"units": [{"unit": self.unit(), "allocated_price": 5500}],
				}
			).insert(ignore_permissions=True)

	# ------------------------------------------------------------ permissions
	def test_sales_user_drafts_sales_manager_submits(self):
		unit = self.unit()
		signing = signing_values()
		with as_user(SALES_USER):
			doc = frappe.get_doc(
				{
					"doctype": "Sidra Sale Contract",
					"customer": BUYER,
					"company": COMPANY,
					"signed_on": "2026-11-05",
					"contract_profile": "Profile A",
					"agreed_price": 5500,
					"units": [{"unit": unit, "allocated_price": 5500}],
					**signing,
				}
			).insert()
			attach_signed_copy(doc)
			with self.assertRaises(frappe.PermissionError):
				doc.submit()
		with as_user(SALES_MANAGER):
			frappe.get_doc("Sidra Sale Contract", doc.name).submit()
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 1)
