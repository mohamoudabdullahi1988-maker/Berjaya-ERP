# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Registering an External contract from Berjaya: allowed fields, stale edits, retries,
permissions, the acknowledged difference (rules audit R1) and no ledger effect."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.contract_registration import (
	StaleRecord,
	attach_registration_copy,
	confirm_registration,
	save_registration_draft,
)
from sidra_realestate.api.workflow import get_contract_timeline
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	ensure_contract_settings,
)
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import EXTERNAL
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_SALES_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_scheme,
	make_unit,
	private_file,
	unique,
)

DOCTYPE = "Sidra Sale Contract"
LEDGER_DOCTYPES = ("GL Entry", "Payment Entry", "Journal Entry", "Sales Invoice")


class TestContractRegistration(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		ensure_contract_settings()
		cls.scheme = make_scheme("_TEST-REG")

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Sidra Contract Settings", "schedule_tolerance", 5)

	# ------------------------------------------------------------ builders
	def values(self, price=9000, schedule=None, **extra):
		unit = make_unit(unique("_T-REG"), self.scheme).name
		rows = (
			schedule
			if schedule is not None
			else [
				{"row_type": "Installment", "due_date": "2026-02-10", "amount": price / 3},
				{"row_type": "Installment", "due_date": "2026-03-10", "amount": price / 3},
				{"row_type": "Installment", "due_date": "2026-04-10", "amount": price / 3},
			]
		)
		return {
			"customer": BUYER,
			"company": COMPANY,
			"signed_on": "2026-01-15",
			"external_reference": unique("EXT-REG"),
			"agreed_price": price,
			"down_payment_mode": "None",
			"installments": len(rows),
			"due_day": 10,
			"units": [{"unit": unit, "allocated_price": price}],
			"schedule": rows,
			**extra,
		}

	def create(self, user=SALES_USER, **values):
		with as_user(user):
			return save_registration_draft(self.values(**values))

	def attach(self, result, user=SALES_USER):
		doc = frappe.get_doc(DOCTYPE, result["name"])
		url = private_file(attached_to=doc)
		with as_user(user):
			return attach_registration_copy(doc.name, url, expected_modified=result["modified"])

	def ready(self, **values):
		"""A draft with everything confirmation needs."""
		return self.attach(self.create(**values))

	def confirm(self, result, user=SALES_MANAGER, **kwargs):
		with as_user(user):
			return confirm_registration(result["name"], expected_modified=result["modified"], **kwargs)

	def ledger_counts(self):
		return {doctype: frappe.db.count(doctype) for doctype in LEDGER_DOCTYPES}

	# ------------------------------------------------------------ drafts
	def test_create_makes_an_external_draft(self):
		result = self.create()
		doc = frappe.get_doc(DOCTYPE, result["name"])
		self.assertEqual((doc.docstatus, doc.contract_type, doc.source), (0, "Installment", EXTERNAL))
		self.assertEqual(len(doc.schedule), 3)
		self.assertEqual(doc.schedule_total, 9000)
		self.assertEqual(doc.schedule_difference, 0)
		self.assertEqual(result["modified"], str(doc.modified))
		self.assertFalse(result["repeated"])

	def test_fields_outside_the_screen_are_refused(self):
		for extra in ({"terms_snapshot": "{}"}, {"docstatus": 1}, {"penalty_type": "None"}, {"source": "x"}):
			with self.subTest(extra=extra), as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
				save_registration_draft({**self.values(), **extra})
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			values = self.values()
			values["schedule"][0]["seq"] = 7
			save_registration_draft(values)

	def test_retry_with_the_same_request_key_makes_one_draft(self):
		values = self.values()
		key = frappe.generate_hash(length=16)
		with as_user(SALES_USER):
			first = save_registration_draft(values, request_key=key)
			second = save_registration_draft(values, request_key=key)
		self.assertEqual(first["name"], second["name"])
		self.assertTrue(second["repeated"])
		self.assertEqual(
			frappe.db.count(DOCTYPE, {"external_reference": values["external_reference"].upper()}), 1
		)

	def test_update_replaces_the_schedule(self):
		result = self.create()
		rows = [{"row_type": "Installment", "due_date": "2026-02-10", "amount": 9000}]
		with as_user(SALES_USER):
			updated = save_registration_draft(
				{"schedule": rows, "installments": 1},
				contract=result["name"],
				expected_modified=result["modified"],
			)
		doc = frappe.get_doc(DOCTYPE, result["name"])
		self.assertEqual([row.amount for row in doc.schedule], [9000])
		self.assertEqual(updated["modified"], str(doc.modified))

	def test_stale_and_unversioned_updates_are_refused(self):
		result = self.create()
		with as_user(SALES_USER):
			save_registration_draft(
				{"terms_summary": "first"}, contract=result["name"], expected_modified=result["modified"]
			)
			with self.assertRaises(StaleRecord):
				save_registration_draft(
					{"terms_summary": "second"}, contract=result["name"], expected_modified=result["modified"]
				)
			with self.assertRaises(StaleRecord):
				save_registration_draft({"terms_summary": "third"}, contract=result["name"])
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "terms_summary"), "first")

	def test_controller_rules_still_apply(self):
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			save_registration_draft(
				self.values(schedule=[{"row_type": "Installment", "due_date": "2026-02-10", "amount": 0}])
			)

	def test_permissions(self):
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			save_registration_draft(self.values())
		result = self.ready()
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			confirm_registration(result["name"], expected_modified=result["modified"])
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "docstatus"), 0)

	def test_generated_or_confirmed_contracts_cannot_be_edited_here(self):
		result = self.ready()
		confirmed = self.confirm(result)
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			save_registration_draft(
				{"terms_summary": "late"}, contract=result["name"], expected_modified=confirmed["modified"]
			)
		generated = self.create()["name"]
		frappe.db.set_value(DOCTYPE, generated, "source", "Generated from profile", update_modified=False)
		modified = str(frappe.db.get_value(DOCTYPE, generated, "modified"))
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			save_registration_draft({"terms_summary": "x"}, contract=generated, expected_modified=modified)

	# ------------------------------------------------------------ signed copy
	def test_signed_copy_must_be_this_contracts_private_file(self):
		result = self.create()
		loose = private_file()
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			attach_registration_copy(result["name"], loose, expected_modified=result["modified"])
		doc = frappe.get_doc(DOCTYPE, result["name"])
		public = private_file(attached_to=doc, is_private=0)
		with as_user(SALES_USER), self.assertRaises(frappe.ValidationError):
			attach_registration_copy(result["name"], public, expected_modified=result["modified"])
		attached = self.attach(result)
		self.assertTrue(frappe.db.get_value(DOCTYPE, attached["name"], "signed_copy"))

	# ------------------------------------------------------------ confirmation
	def test_confirm_marks_units_and_posts_nothing(self):
		result = self.ready()
		before = self.ledger_counts()
		confirmed = self.confirm(result)
		doc = frappe.get_doc(DOCTYPE, result["name"])
		self.assertEqual((confirmed["docstatus"], doc.docstatus), (1, 1))
		self.assertEqual(doc.terms_approved_by, SALES_MANAGER)
		self.assertEqual(frappe.db.get_value("Sidra Unit", doc.units[0].unit, "status"), "Under Contract")
		self.assertEqual(self.ledger_counts(), before)
		with as_user(SALES_MANAGER):
			states = [stage["state"] for stage in get_contract_timeline(doc.name)["stages"]]
		self.assertEqual(set(states), {"completed"})

	def test_repeated_confirmation_changes_nothing(self):
		result = self.ready()
		first = self.confirm(result)
		modified = frappe.db.get_value(DOCTYPE, result["name"], "modified")
		again = self.confirm(result)
		self.assertTrue(again["repeated"])
		self.assertEqual(again["name"], first["name"])
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "modified"), modified)
		with as_user(OTHER_SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			confirm_registration(result["name"], expected_modified=first["modified"])

	def test_stale_confirmation_is_refused(self):
		result = self.ready()
		with as_user(SALES_MANAGER), self.assertRaises(StaleRecord):
			confirm_registration(result["name"], expected_modified="2000-01-01 00:00:00")
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "docstatus"), 0)

	def test_difference_within_tolerance_needs_acknowledgement(self):
		rows = [{"row_type": "Installment", "due_date": "2026-02-10", "amount": 8997}]
		result = self.ready(schedule=rows)
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			confirm_registration(result["name"], expected_modified=result["modified"])
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "docstatus"), 0)
		self.confirm(result, acknowledge_difference=1)
		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": DOCTYPE, "reference_name": result["name"], "comment_type": "Info"},
			pluck="content",
		)
		self.assertTrue(any("acknowledged" in (text or "") for text in comments), comments)

	def test_difference_above_tolerance_is_refused_even_when_acknowledged(self):
		rows = [{"row_type": "Installment", "due_date": "2026-02-10", "amount": 8000}]
		result = self.ready(schedule=rows)
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			confirm_registration(
				result["name"], expected_modified=result["modified"], acknowledge_difference=1
			)
		self.assertEqual(frappe.db.get_value(DOCTYPE, result["name"], "docstatus"), 0)
