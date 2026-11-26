# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Registering External contracts (docs/CONTRACT-CAPTURE_v0.3.md §6.4; CC-01 to CC-10; D1-D7, issue #13)."""

import json
from datetime import date

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.patches.v0_3 import set_contract_source
from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	ensure_contract_settings,
)
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import (
	EXTERNAL,
	GENERATED,
	propose_schedule,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_BUYER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	ensure_fiscal_year,
	make_held_profile,
	make_scheme,
	make_unit,
	signing_values,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Customer", "Company", "Sidra Contract Profile", "User"]

# Confirmation posts nothing. A Sales Order is not a ledger record: since G40 (25 Nov 2026) a confirmed
# contract gets exactly one as its ERPNext Selling copy, checked where a contract is registered.
LEDGER_DOCTYPES = (
	"Sales Invoice",
	"Payment Entry",
	"Journal Entry",
	"GL Entry",
	"Payment Ledger Entry",
)


def rows(*items):
	"""(type, 'YYYY-MM-DD', amount) tuples as schedule rows."""
	return [{"row_type": t, "due_date": d, "amount": a} for t, d, a in items]


def installments(n, amount, start_year=2026, start_month=4, day=10):
	out = []
	for i in range(n):
		index = start_year * 12 + start_month - 1 + i
		out.append(("Installment", f"{index // 12}-{index % 12 + 1:02d}-{day:02d}", amount))
	return out


class TestContractCapture(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		ensure_contract_settings()
		ensure_fiscal_year("2026-01-15")  # G40: the Sales Order copy needs one for the signing date
		cls.scheme = make_scheme("_TEST-CAP")

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Sidra Contract Settings", "schedule_tolerance", 5)

	def unit(self):
		return make_unit(unique("_T-CAP"), self.scheme).name

	def external(self, price=10000, schedule=None, *, units=None, attach=True, **values):
		units = units or [self.unit()]
		share = price / len(units)
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": EXTERNAL,
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-01-15",
				"agreed_price": price,
				"units": [{"unit": u, "allocated_price": share} for u in units],
				"external_reference": unique("EXT-DEMO"),
				"schedule": rows(*([("Installment", "2026-02-10", price)] if schedule is None else schedule)),
				**values,
			}
		).insert(ignore_permissions=True)
		return attach_signed_copy(doc) if attach else doc

	def confirm(self, doc):
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc("Sidra Sale Contract", doc.name)
			doc.submit()
		return doc

	def assert_refused(self, doc, *fragments):
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)) as caught:
			self.confirm(doc)
		for fragment in fragments:
			self.assertIn(fragment, str(caught.exception))
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 0)

	# ------------------------------------------------------------ acceptance scenario
	def test_register_external_contract_irregular_schedule(self):
		u1, u2 = self.unit(), self.unit()
		reference = unique("EXT-DEMO-0001")
		schedule = [
			("Installment", "2026-01-15", 2500),
			("Installment", "2026-01-15", 2500),  # same day: allowed (CC-05)
			("Installment", "2026-03-02", 1000),
			("Installment", "2026-04-28", 1000),
			("Installment", "2026-07-01", 1000),
			("Installment", "2026-07-19", 1000),
			("Installment", "2026-12-31", 1000),
		]
		before = {dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}
		doc = self.external(10000, schedule, units=[u1, u2], external_reference=reference)

		reopened = frappe.get_doc("Sidra Sale Contract", doc.name)
		self.assertEqual(
			[(r.seq, r.row_type, getdate(r.due_date), r.amount) for r in reopened.schedule],
			[(i, t, getdate(d), a) for i, (t, d, a) in enumerate(schedule, start=1)],
		)
		self.assertEqual(reopened.external_reference, reference.upper())
		self.assertTrue(reopened.signed_copy)
		self.assertEqual(
			(reopened.schedule_total, reopened.amount_due, reopened.schedule_difference), (10000, 10000, 0)
		)

		confirmed = self.confirm(reopened)
		self.assertEqual(confirmed.docstatus, 1)
		self.assertEqual(len(confirmed.schedule), 7)  # nothing regenerated at confirmation
		self.assertEqual(confirmed.terms_approved_by, SALES_MANAGER)
		self.assertTrue(confirmed.terms_approved_on)
		snapshot = json.loads(confirmed.terms_snapshot)
		self.assertEqual(snapshot["source"], EXTERNAL)
		self.assertEqual(snapshot["external_reference"], reference.upper())
		self.assertEqual(snapshot["terms_approved_by"], SALES_MANAGER)
		self.assertEqual(snapshot["schedule_difference"], 0)
		for unit in (u1, u2):
			self.assertEqual(
				frappe.db.get_value("Sidra Unit", unit, ["status", "current_contract"]),
				("Under Contract", doc.name),
			)
		self.assertEqual({dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}, before)
		copies = frappe.get_all(
			"Sales Order", filters={"sidra_sale_contract": doc.name, "docstatus": 1}, fields=["grand_total"]
		)
		self.assertEqual([row.grand_total for row in copies], [confirmed.agreed_price])  # G40

	# ------------------------------------------------------------ propose_schedule (CC-06)
	def test_propose_schedule_only_when_asked(self):
		doc = self.external(9000, schedule=[], installments=24, due_day=10, grace_months=3)
		self.assertEqual(doc.schedule, [])
		propose_schedule(doc.name)
		doc.reload()
		self.assertEqual([r.amount for r in doc.schedule], [375] * 24)
		self.assertEqual(getdate(doc.schedule[0].due_date), date(2026, 4, 10))

		with self.assertRaises(frappe.ValidationError):
			propose_schedule(doc.name)  # rows exist: refused without replace

		doc.schedule[0].amount = 400  # proposed rows stay editable
		doc.schedule[1].amount = 350
		doc.save()
		doc.reload()
		self.assertEqual((doc.schedule[0].amount, doc.schedule[1].amount), (400, 350))

		propose_schedule(doc.name, replace=1)
		doc.reload()
		self.assertEqual([r.amount for r in doc.schedule], [375] * 24)

	def test_propose_with_down_payment_included(self):
		doc = self.external(
			9000,
			schedule=[],
			installments=24,
			due_day=10,
			grace_months=3,
			down_payment_mode="Included in schedule",
		)
		propose_schedule(doc.name, down_payment=3000)
		doc.reload()
		self.assertEqual((doc.schedule[0].row_type, doc.schedule[0].amount), ("Down payment", 3000))
		self.assertEqual([r.amount for r in doc.schedule[1:]], [250] * 24)
		self.assertEqual((doc.down_payment, doc.schedule_difference), (3000, 0))

	# ------------------------------------------------------------ reconciliation (D1-D3)
	def test_d1_included_in_schedule(self):
		doc = self.external(
			9000,
			[("Down payment", "2026-01-15", 3000), *installments(24, 250)],
			down_payment_mode="Included in schedule",
		)
		self.assertEqual((doc.down_payment, doc.amount_due, doc.schedule_difference), (3000, 9000, 0))
		self.assertEqual(self.confirm(doc).docstatus, 1)

	def test_d1_recorded_separately(self):
		doc = self.external(
			9000, installments(24, 250), down_payment_mode="Recorded separately", down_payment=3000
		)
		self.assertEqual((doc.amount_due, doc.schedule_total, doc.schedule_difference), (6000, 6000, 0))
		confirmed = self.confirm(doc)
		snapshot = json.loads(confirmed.terms_snapshot)
		self.assertEqual(
			(snapshot["down_payment_mode"], snapshot["down_payment"]), ("Recorded separately", 3000)
		)

	def test_d1_mixing_modes_refused(self):
		for mode in ("Recorded separately", "None"):
			with self.subTest(mode=mode), self.assertRaises(frappe.ValidationError):
				self.external(
					9000,
					[("Down payment", "2026-01-15", 3000), *installments(24, 250)],
					down_payment_mode=mode,
					down_payment=3000,
				)

	def test_d1_included_needs_a_down_payment_row(self):
		doc = self.external(6000, installments(24, 250), down_payment_mode="Included in schedule")
		self.assert_refused(doc, "Down payment row")

	def test_d2_fee_rows_count(self):
		doc = self.external(10200, [*installments(10, 1000), ("Fee", "2026-01-15", 200)])
		self.assertEqual((doc.schedule_total, doc.schedule_difference), (10200, 0))
		self.assertEqual(self.confirm(doc).docstatus, 1)

		fee_outside_price = self.external(10000, [*installments(10, 1000), ("Fee", "2026-01-15", 200)])
		self.assertEqual(fee_outside_price.schedule_difference, -200)
		self.assert_refused(fee_outside_price, "more than the limit")

	def test_d3_tolerance(self):
		for difference, confirms in ((4, True), (5, True), (5.01, False), (-5.01, False), (-5, True)):
			with self.subTest(difference=difference):
				doc = self.external(10000, [("Installment", "2026-02-10", 10000 - difference)])
				self.assertEqual(doc.schedule_difference, difference)  # saving always works
				if confirms:
					snapshot = json.loads(self.confirm(doc).terms_snapshot)
					self.assertEqual(
						(snapshot["schedule_difference"], snapshot["schedule_tolerance"]), (difference, 5)
					)
				else:
					self.assert_refused(doc, "more than the limit")

	def test_d3_setting_change_does_not_touch_confirmed_snapshot(self):
		confirmed = self.confirm(self.external(10000, [("Installment", "2026-02-10", 9996)]))
		frappe.db.set_single_value("Sidra Contract Settings", "schedule_tolerance", 1)
		snapshot = json.loads(frappe.db.get_value("Sidra Sale Contract", confirmed.name, "terms_snapshot"))
		self.assertEqual(snapshot["schedule_tolerance"], 5)
		self.assert_refused(
			self.external(10000, [("Installment", "2026-02-10", 9996)]), "more than the limit"
		)

	# ------------------------------------------------------------ D4 and holds
	def test_contract_b_type_registration_confirms(self):
		doc = self.external(
			9000,
			installments(24, 250),
			contract_profile="Profile B",
			down_payment_mode="Recorded separately",
			down_payment=3000,
		)
		self.assertEqual((doc.installments, doc.due_day, doc.grace_months), (24, 10, 3))
		self.assertEqual(doc.title_deadline_days, 20)
		self.assertEqual(self.confirm(doc).docstatus, 1)

	def test_profile_optional_but_held_profile_blocks(self):
		self.assertEqual(self.confirm(self.external()).docstatus, 1)  # no profile
		doc = self.external(contract_profile=make_held_profile().name)
		self.assert_refused(doc, "legal hold")

	# ------------------------------------------------------------ external reference
	def test_external_reference_required_normalised_and_unique(self):
		self.assert_refused(self.external(external_reference=None), "external reference")

		reference = unique("ext-demo")
		first = self.external(external_reference=f"  {reference}  ")
		self.assertEqual(first.external_reference, reference.upper())
		second = self.external(external_reference=reference.upper(), customer=OTHER_BUYER)  # drafts may share
		self.confirm(first)
		self.assert_refused(second, "already used")

	# ------------------------------------------------------------ D5 signing data
	def test_d5_external_without_parties_or_notary_confirms(self):
		doc = self.external(parties=[], notary_name=None, notary_reference=None)
		self.assertEqual(self.confirm(doc).docstatus, 1)

	def test_d5_original_document_required(self):
		self.assert_refused(self.external(attach=False), "original signed contract")

	def test_d5_present_values_still_validated(self):
		with self.assertRaises(frappe.ValidationError):
			self.external(notary_reference="NOT-A-REFERENCE")
		doc = self.external(parties=[{"role": "Seller Guarantor", "full_name": "_Test Guarantor"}])
		self.assert_refused(doc, "pledged property")

	def test_d5_generated_contract_keeps_full_gate(self):
		unit = self.unit()
		values = signing_values()
		values["parties"] = [p for p in values["parties"] if p["role"] != "Witness"]
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"contract_profile": "Profile A",
				"agreed_price": 14000,
				"units": [{"unit": unit, "allocated_price": 14000}],
				**values,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.source, GENERATED)
		attach_signed_copy(doc)
		self.assert_refused(doc, "two Witnesses")

	# ------------------------------------------------------------ D6 captured terms
	def test_d6_prefilled_editable_validated_frozen_never_applied(self):
		doc = self.external(9000, installments(24, 250), contract_profile="Profile B")
		self.assertEqual(
			(doc.down_payment_mode, doc.down_payment, doc.schedule_difference),
			("Recorded separately", 3000, 0),
		)
		self.assertEqual(
			(doc.penalty_type, doc.penalty_fixed_amount, doc.notice_days, doc.title_penalty_amount),
			("Fixed After Notice", 100, 15, 220),
		)
		self.assertEqual(
			(doc.notice_last_day, doc.receipt_order, doc.title_part_month, doc.title_refund_from),
			("Counts as Late", "Installments", "Pending Decision", "Pending Decision"),
		)
		doc.notice_days = 61
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		doc.reload()
		doc.notice_days = 20  # editable in a draft
		doc.title_part_month = "Charged as Full Month"  # issue #3 rules are captured terms too
		doc.save()

		before = {
			dt: frappe.db.count(dt)
			for dt in (*LEDGER_DOCTYPES, "Sidra Reservation", "Sidra Contract Profile")
		}
		confirmed = self.confirm(doc)
		snapshot = json.loads(confirmed.terms_snapshot)
		self.assertEqual((snapshot["notice_days"], snapshot["penalty_fixed_amount"]), (20, 100))
		self.assertEqual(snapshot["title_part_month"], "Charged as Full Month")
		self.assertEqual(
			{
				dt: frappe.db.count(dt)
				for dt in (*LEDGER_DOCTYPES, "Sidra Reservation", "Sidra Contract Profile")
			},
			before,
		)

		confirmed.notice_days = 30
		with self.assertRaises(frappe.ValidationError):
			confirmed.save()

	# ------------------------------------------------------------ D7 and locking
	def test_d7_sales_user_cannot_confirm(self):
		doc = self.external()
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Sidra Sale Contract", doc.name).submit()

	def test_rows_read_only_after_confirmation(self):
		confirmed = self.confirm(self.external())
		confirmed.schedule[0].amount = 1
		with self.assertRaises(frappe.ValidationError):
			confirmed.save()

	def test_revise_draft_refused_for_external(self):
		from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import revise_draft

		with self.assertRaises(frappe.ValidationError):
			revise_draft(self.external().name)

	# ------------------------------------------------------------ migration
	def test_migration_marks_existing_contracts_generated(self):
		doc = self.external(10000, installments(10, 1000))
		frappe.db.set_value("Sidra Sale Contract", doc.name, "source", None)
		frappe.db.sql(
			"update `tabSidra Installment Line` set row_type=NULL where parent=%s",
			(doc.name,),
		)
		set_contract_source.execute()
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "source"), GENERATED)
		self.assertEqual(
			set(frappe.get_all("Sidra Installment Line", filters={"parent": doc.name}, pluck="row_type")),
			{"Installment"},
		)
