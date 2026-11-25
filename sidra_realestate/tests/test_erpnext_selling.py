# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""G39: issued Sidra quotations and confirmed Sidra contracts appear in ERPNext Selling."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.services.erpnext_selling import (
	SALE_ITEMS,
	backfill_selling,
	ensure_selling_setup,
	sync_selling,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_confirmed_contract,
	make_scheme,
	make_unit,
	unique,
)

QUOTATION = "Sidra Sale Quotation"
SCHEME = "_T-SEL"


class TestERPNextSelling(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		ensure_selling_setup()

	def issued_quotation(self, units):
		with as_user(SALES_USER):
			doc = frappe.get_doc(
				{
					"doctype": QUOTATION,
					"customer": BUYER,
					"contract_profile": "Profile A",
					"units": [{"unit": u, "installment_price": price} for u, price in units],
				}
			).insert()
		with as_user(SALES_USER):  # as the quotation tests issue it
			doc = frappe.get_doc(QUOTATION, doc.name)
			doc.submit()
		return doc

	def copy(self, doctype, link, name):
		names = frappe.get_all(doctype, filters={link: name, "docstatus": 1}, pluck="name")
		notes = frappe.get_all(
			"Comment", filters={"reference_name": name, "comment_type": "Info"}, pluck="content"
		)
		self.assertEqual(len(names), 1, f"{doctype} copies of {name}; notes: {notes}")
		return frappe.get_doc(doctype, names[0])

	def test_setup_items(self):
		for item in SALE_ITEMS.values():
			values = frappe.db.get_value("Item", item, ["is_stock_item", "is_sales_item"], as_dict=True)
			self.assertEqual((values.is_stock_item, values.is_sales_item), (0, 1))

	def test_issued_quotation_becomes_an_erpnext_quotation(self):
		scheme = make_scheme(SCHEME)
		plot = make_unit(unique("_T-SELP"), scheme, cash_price=11000).name
		house = make_unit(unique("_T-SELH"), scheme, cash_price=30000, unit_type="House").name
		sidra = self.issued_quotation([(plot, 11000), (house, 31000)])
		copy = self.copy("Quotation", "sidra_sale_quotation", sidra.name)
		self.assertEqual((copy.party_name, copy.company), (BUYER, COMPANY))
		lines = {row.sidra_unit: row for row in copy.items}
		self.assertEqual(lines[plot].item_code, SALE_ITEMS["Plot"])
		self.assertEqual(lines[house].item_code, SALE_ITEMS["House"])
		self.assertEqual((lines[house].rate, lines[house].price_list_rate), (31000, 30000))
		self.assertEqual(copy.grand_total, sidra.installment_total)

		# The copy follows its Sidra quotation: not even a System Manager cancels it by hand.
		with as_user("Administrator"), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Quotation", copy.name).cancel()
		with as_user("Administrator"):
			frappe.get_doc(QUOTATION, sidra.name).cancel()
		self.assertEqual(frappe.db.get_value("Quotation", copy.name, "docstatus"), 2)

	def test_confirmed_contract_becomes_a_sales_order(self):
		contract = make_confirmed_contract(SCHEME)
		order = self.copy("Sales Order", "sidra_sale_contract", contract.name)
		self.assertEqual((order.customer, order.company), (BUYER, COMPANY))
		self.assertEqual(order.grand_total, contract.agreed_price)
		self.assertEqual([row.sidra_unit for row in order.items], [row.unit for row in contract.units])
		self.assertEqual(frappe.db.count("GL Entry", {"voucher_no": order.name}), 0)

	def test_a_failed_copy_never_blocks_the_contract(self):
		contract = make_confirmed_contract(SCHEME)  # the copy is made here
		order = self.copy("Sales Order", "sidra_sale_contract", contract.name)
		# A broken unit type: the copy fails, the contract stays confirmed and says so.
		frappe.db.set_value("Sidra Unit", contract.units[0].unit, "unit_type", None)
		frappe.flags["sidra_selling_sync"] = True
		frappe.get_doc("Sales Order", order.name).cancel()
		frappe.flags["sidra_selling_sync"] = False
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			sync_selling("Sidra Sale Contract", contract.name)
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", contract.name, "docstatus"), 1)
		frappe.db.set_value("Sidra Unit", contract.units[0].unit, "unit_type", "Plot")
		with as_user(SALES_MANAGER):
			made = sync_selling("Sidra Sale Contract", contract.name)["created"]
		self.assertTrue(made)

	def test_sync_needs_submit_rights(self):
		contract = make_confirmed_contract(SCHEME)
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			sync_selling("Sidra Sale Contract", contract.name)

	def test_backfill_makes_only_missing_copies(self):
		contract = make_confirmed_contract(SCHEME)
		order = self.copy("Sales Order", "sidra_sale_contract", contract.name)
		frappe.flags["sidra_selling_sync"] = True
		frappe.get_doc("Sales Order", order.name).cancel()
		frappe.flags["sidra_selling_sync"] = False
		with as_user("Administrator"):
			result = backfill_selling(company=COMPANY)
		self.assertIn(contract.name, result["made"])
		with as_user("Administrator"):
			again = backfill_selling(company=COMPANY)
		self.assertNotIn(contract.name, again["made"])
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			backfill_selling()
