# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The Berjaya form engine for sales (G23, step 2): price changes, quotations, cash and generated
contracts, Revise draft, title transfers. Real records; every rule is the controller's."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.api.forms import get_form, run_action, save_form, submit_form
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	GENERAL_MANAGER,
	OTHER_SALES_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_confirmed_contract,
	make_scheme,
	make_unit,
	private_file,
	signing_values,
	unique,
)

SCHEME = "_TEST-FORMS-SALES"


def fields_of(form):
	return {field["fieldname"]: field for section in form["layout"] for field in section["fields"]}


def keys(form):
	return [action["key"] for action in form["actions"]]


class TestFormsSales(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		make_scheme(SCHEME)

	def unit(self, price=11000):
		return make_unit(unique("_T-FS"), SCHEME, cash_price=price).name

	def test_price_change_is_created_and_submitted(self):
		unit = self.unit(0)  # no price yet, so no history entry to come after
		with as_user(SALES_MANAGER):
			created = save_form(
				"Sidra Unit Price History",
				{"unit": unit, "price": 12500, "effective_from": today(), "reason": "Review"},
			)
			submitted = submit_form(
				"Sidra Unit Price History", created["name"], expected_modified=created["modified"]
			)
		self.assertEqual(submitted["docstatus"], 1)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "cash_price"), 12500)
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			save_form(
				"Sidra Unit Price History",
				{"unit": unit, "price": 1, "effective_from": today(), "reason": "x"},
			)

	def test_quotation_discount_is_approved_by_a_second_person(self):
		with as_user(SALES_USER):
			form = get_form("Sidra Sale Quotation")
			self.assertEqual(
				fields_of(form)["units"]["columns"][0]["link_filters"],
				{"status": ["in", ["Available", "Reserved"]]},
			)
			created = save_form(
				"Sidra Sale Quotation",
				{
					"customer": BUYER,
					"contract_profile": "Profile A",
					"units": [{"unit": self.unit(), "cash_price": 10600, "installment_price": 11000}],
				},
			)
		doc = frappe.get_doc("Sidra Sale Quotation", created["name"])
		self.assertEqual(doc.discount_approval, "Sidra Sales Manager")
		with as_user(SALES_USER):
			self.assertEqual(keys(get_form("Sidra Sale Quotation", doc.name)), [])  # not a manager
			with self.assertRaises(frappe.ValidationError):  # issuing needs the approval first
				submit_form("Sidra Sale Quotation", doc.name, expected_modified=created["modified"])
		with as_user(SALES_MANAGER):
			self.assertEqual(keys(get_form("Sidra Sale Quotation", doc.name)), ["approve_discount"])
			run_action("Sidra Sale Quotation", doc.name, "approve_discount", {}, created["modified"])
		modified = str(frappe.db.get_value("Sidra Sale Quotation", doc.name, "modified"))
		with as_user(SALES_USER):
			issued = submit_form("Sidra Sale Quotation", doc.name, expected_modified=modified)
		self.assertEqual(issued["docstatus"], 1)

	def test_preparer_is_not_offered_the_approval(self):
		with as_user(OTHER_SALES_MANAGER):  # a manager who can read customers
			created = save_form(
				"Sidra Sale Quotation",
				{
					"customer": BUYER,
					"contract_profile": "Profile A",
					"units": [{"unit": self.unit(), "cash_price": 10600, "installment_price": 11000}],
				},
			)
			self.assertEqual(keys(get_form("Sidra Sale Quotation", created["name"])), [])

	def test_cash_contract_created_signed_and_revised(self):
		unit = self.unit(5000)
		values = {
			"contract_type": "Cash",
			"customer": BUYER,
			"company": COMPANY,
			"signed_on": today(),
			"agreed_price": 5000,
			"units": [{"unit": unit, "allocated_price": 5000}],
			**signing_values(),
		}
		values.pop("source")
		with as_user(SALES_USER):
			created = save_form("Sidra Sale Contract", values)
			form = get_form("Sidra Sale Contract", created["name"])
			self.assertEqual(keys(form), ["revise_draft"])
			self.assertFalse(form["permissions"]["submit"])  # Sales User cannot sign
		doc = frappe.get_doc("Sidra Sale Contract", created["name"])
		url = private_file(attached_to=doc)
		with as_user(SALES_USER):
			created = save_form(
				"Sidra Sale Contract",
				{"signed_copy": url},
				name=doc.name,
				expected_modified=created["modified"],
			)
		with as_user(SALES_MANAGER):
			signed = submit_form("Sidra Sale Contract", doc.name, expected_modified=created["modified"])
		self.assertEqual(signed["docstatus"], 1)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")
		with as_user(SALES_MANAGER):
			self.assertEqual(keys(get_form("Sidra Sale Contract", doc.name)), [])  # no Revise once signed

	def test_revise_draft_opens_the_new_draft(self):
		values = {
			"contract_type": "Installment",
			"customer": BUYER,
			"company": COMPANY,
			"contract_profile": "Profile A",
			"signed_on": today(),
			"agreed_price": 11000,
			"units": [{"unit": self.unit(), "allocated_price": 11000}],
			**signing_values(),
		}
		with as_user(SALES_USER):
			created = save_form("Sidra Sale Contract", values)
			result = run_action(
				"Sidra Sale Contract", created["name"], "revise_draft", {}, created["modified"]
			)
		self.assertEqual(result["open"]["doctype"], "Sidra Sale Contract")
		self.assertNotEqual(result["open"]["name"], created["name"])
		self.assertTrue(frappe.db.exists("Sidra Sale Contract", result["open"]["name"]))

	def test_registered_contract_is_not_submitted_through_the_form(self):
		values = {
			"contract_type": "Installment",
			"source": "External (registered)",
			"customer": BUYER,
			"company": COMPANY,
			"signed_on": today(),
			"external_reference": unique("EXT-FS"),
			"agreed_price": 3000,
			"units": [{"unit": self.unit(3000), "allocated_price": 3000}],
			"schedule": [{"row_type": "Installment", "due_date": add_days(today(), 30), "amount": 3000}],
		}
		with as_user(SALES_USER):
			created = save_form("Sidra Sale Contract", values)
		with as_user(SALES_MANAGER):
			form = get_form("Sidra Sale Contract", created["name"])
			self.assertFalse(form["permissions"]["submit"])  # confirmed on its registration screen (G22)
			self.assertEqual(keys(form), [])
			with self.assertRaises(frappe.ValidationError):
				submit_form("Sidra Sale Contract", created["name"], expected_modified=created["modified"])

	def test_title_transfer_confirmations(self):
		contract = make_confirmed_contract(SCHEME)
		with as_user(SALES_MANAGER):
			form = get_form("Sidra Title Transfer")
			self.assertEqual(fields_of(form)["contract"]["link_filters"], {"docstatus": 1})
			created = save_form(
				"Sidra Title Transfer", {"contract": contract.name, "unit": contract.units[0].unit}
			)
		doc = frappe.get_doc("Sidra Title Transfer", created["name"])
		evidence = private_file(name="receipt.pdf", attached_to=doc, field="final_payment_evidence")
		with as_user(SALES_MANAGER):
			created = save_form(
				"Sidra Title Transfer",
				{"final_payment_date": add_days(today(), -2), "final_payment_evidence": evidence},
				name=doc.name,
				expected_modified=created["modified"],
			)
			self.assertEqual(
				keys(get_form("Sidra Title Transfer", doc.name)), []
			)  # entered it: not the confirmer
		with as_user(OTHER_SALES_MANAGER):
			self.assertEqual(keys(get_form("Sidra Title Transfer", doc.name)), ["confirm_final_payment"])
			run_action("Sidra Title Transfer", doc.name, "confirm_final_payment", {}, created["modified"])
		doc.reload()
		self.assertTrue(doc.final_payment_confirmed_on)
		handover = private_file(name="handover.pdf", attached_to=doc, field="handover_evidence")
		with as_user(SALES_MANAGER):
			updated = save_form(
				"Sidra Title Transfer",
				{
					"deed_number": "DEED-FS-1",
					"handed_over_on": today(),
					"handed_over_to": "_Test Buyer Amina",
					"handover_evidence": handover,
				},
				name=doc.name,
				expected_modified=str(doc.modified),
			)
		with as_user(GENERAL_MANAGER):
			self.assertEqual(keys(get_form("Sidra Title Transfer", doc.name)), ["confirm_handover"])
			run_action("Sidra Title Transfer", doc.name, "confirm_handover", {}, updated["modified"])
		self.assertTrue(frappe.db.get_value("Sidra Title Transfer", doc.name, "handover_confirmed_on"))
