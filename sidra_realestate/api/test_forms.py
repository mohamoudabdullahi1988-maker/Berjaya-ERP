# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The Berjaya form engine (G23): form description, field allowlist, rules, stale edits, retries,
actions and permissions, against real records."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.forms import (
	StaleRecord,
	cancel_form,
	delete_form,
	get_form,
	run_action,
	save_form,
	submit_form,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_SALES_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	ensure_customer,
	make_scheme,
	private_file,
	unique,
)


def fields_of(form):
	return {field["fieldname"]: field for section in form["layout"] for field in section["fields"]}


class TestForms(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.scheme = make_scheme("_TEST-FORMS")

	def unit_values(self, **extra):
		return {
			"unit_code": unique("_T-FORM"),
			"scheme": self.scheme,
			"unit_type": "Plot",
			"cash_price": 12000,
			**extra,
		}

	def create_unit(self, user=SALES_MANAGER, **extra):
		with as_user(user):
			return save_form("Sidra Unit", self.unit_values(**extra))

	# ------------------------------------------------------------ describing a form
	def test_form_describes_fields_rules_and_permissions(self):
		with as_user(SALES_MANAGER):
			new = get_form("Sidra Unit")
		fields = fields_of(new)
		self.assertTrue(new["is_new"])
		self.assertTrue(fields["unit_code"]["editable"] and fields["unit_code"]["reqd"])
		self.assertFalse(fields["company"]["editable"])  # read-only: fetched from the scheme
		self.assertEqual(fields["cash_price"]["read_only_rule"], {"not": {"field": "__islocal"}})
		self.assertEqual(fields["unit_type"]["fieldtype"], "Select")
		self.assertIn("Plot", fields["unit_type"]["options"])
		self.assertEqual(new["actions"], [])

		created = self.create_unit()
		with as_user(SALES_USER):
			form = get_form("Sidra Unit", created["name"])
		self.assertFalse(form["permissions"]["write"])  # Sales User reads units only
		self.assertFalse(any(field["editable"] for field in fields_of(form).values()))
		self.assertEqual([action["key"] for action in form["actions"]], ["reserve_unit"])
		self.assertEqual(form["values"]["name"], created["name"])
		self.assertEqual(form["modified"], created["modified"])
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			get_form("Sidra Unit", created["name"])

	def test_types_outside_the_engine_are_refused(self):
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			get_form("User", "Administrator")
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			save_form("ToDo", {"description": "x"})

	# ------------------------------------------------------------ writing
	def test_create_update_and_controller_rules(self):
		created = self.create_unit()
		doc = frappe.get_doc("Sidra Unit", created["name"])
		self.assertEqual((doc.company, doc.cash_price), (COMPANY, 12000))  # company fetched by the controller
		with as_user(SALES_MANAGER):
			updated = save_form(
				"Sidra Unit", {"area_sqm": 216}, name=doc.name, expected_modified=created["modified"]
			)
		self.assertEqual(frappe.db.get_value("Sidra Unit", doc.name, "area_sqm"), 216)
		self.assertEqual(updated["modified"], str(frappe.db.get_value("Sidra Unit", doc.name, "modified")))
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			save_form("Sidra Unit", self.unit_values(unit_type="Spaceship"))

	def test_fields_outside_the_form_are_refused(self):
		created = self.create_unit()
		for values in ({"company": "x"}, {"current_contract": "x"}, {"docstatus": 1}, {"owner": "x"}):
			with (
				self.subTest(values=values),
				as_user(SALES_MANAGER),
				self.assertRaises(frappe.ValidationError),
			):
				save_form("Sidra Unit", values, name=created["name"], expected_modified=created["modified"])

	def test_read_only_by_rule_is_enforced_on_the_server(self):
		created = self.create_unit()
		with as_user(SALES_MANAGER):
			with self.assertRaises(frappe.ValidationError):  # price changes need price history
				save_form(
					"Sidra Unit",
					{"cash_price": 99},
					name=created["name"],
					expected_modified=created["modified"],
				)
			# The same value sent back unchanged is fine.
			save_form(
				"Sidra Unit",
				{"cash_price": 12000},
				name=created["name"],
				expected_modified=created["modified"],
			)
		self.assertEqual(frappe.db.get_value("Sidra Unit", created["name"], "cash_price"), 12000)

	def test_stale_unversioned_and_permission(self):
		created = self.create_unit()
		with as_user(SALES_MANAGER):
			save_form(
				"Sidra Unit", {"area_sqm": 1}, name=created["name"], expected_modified=created["modified"]
			)
			with self.assertRaises(StaleRecord):
				save_form(
					"Sidra Unit", {"area_sqm": 2}, name=created["name"], expected_modified=created["modified"]
				)
			with self.assertRaises(StaleRecord):
				save_form("Sidra Unit", {"area_sqm": 3}, name=created["name"])
		modified = str(frappe.db.get_value("Sidra Unit", created["name"], "modified"))
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			save_form("Sidra Unit", {"area_sqm": 4}, name=created["name"], expected_modified=modified)
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			save_form("Sidra Unit", self.unit_values())
		self.assertEqual(frappe.db.get_value("Sidra Unit", created["name"], "area_sqm"), 1)

	def test_request_key_makes_one_record(self):
		values = self.unit_values()
		key = frappe.generate_hash(length=16)
		with as_user(SALES_MANAGER):
			first = save_form("Sidra Unit", values, request_key=key)
			second = save_form("Sidra Unit", values, request_key=key)
		self.assertEqual(first["name"], second["name"])
		self.assertTrue(second["repeated"])

	def test_create_only_fields(self):
		name = unique("_Test Form Customer")
		with as_user(SALES_USER):  # ERPNext Sales User may create customers
			form = get_form("Customer")
			self.assertTrue(fields_of(form)["mobile_no"]["editable"])
			created = save_form(
				"Customer",
				{"customer_name": name, "customer_type": "Individual", "mobile_no": "+252634000000"},
			)
			self.assertFalse(fields_of(get_form("Customer", created["name"]))["mobile_no"]["editable"])
			with self.assertRaises(frappe.ValidationError):
				save_form(
					"Customer",
					{"mobile_no": "1"},
					name=created["name"],
					expected_modified=created["modified"],
				)
		self.assertEqual(frappe.db.get_value("Customer", created["name"], "customer_name"), name)

	def test_delete_needs_delete_permission(self):
		with as_user(SALES_MANAGER):
			created = save_form(
				"Sidra Scheme",
				{"scheme_code": unique("_T-DEL"), "scheme_name": "_Test deletable", "company": COMPANY},
			)
			with self.assertRaises(frappe.PermissionError):  # Sales Manager has no delete right
				delete_form("Sidra Scheme", created["name"], expected_modified=created["modified"])
		with as_user("Administrator"):
			result = delete_form("Sidra Scheme", created["name"], expected_modified=created["modified"])
			again = delete_form("Sidra Scheme", created["name"], expected_modified=created["modified"])
		self.assertTrue(result["deleted"] and again["repeated"])
		self.assertFalse(frappe.db.exists("Sidra Scheme", created["name"]))

	def test_submit_and_cancel_need_a_submittable_type(self):
		created = self.create_unit()
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			submit_form("Sidra Unit", created["name"], expected_modified=created["modified"])
		with as_user(SALES_MANAGER), self.assertRaises(frappe.ValidationError):
			cancel_form("Sidra Unit", created["name"], expected_modified=created["modified"])

	# ------------------------------------------------------------ actions
	def test_reserve_and_cancel_actions(self):
		created = self.create_unit()
		with as_user(SALES_USER):
			with self.assertRaises(frappe.ValidationError):  # values not part of the action
				run_action(
					"Sidra Unit",
					created["name"],
					"reserve_unit",
					{"customer": BUYER, "status": "x"},
					created["modified"],
				)
			result = run_action(
				"Sidra Unit",
				created["name"],
				"reserve_unit",
				{"customer": BUYER, "days": 3},
				created["modified"],
			)
		self.assertIn("reservation", result)
		unit = frappe.get_doc("Sidra Unit", created["name"])
		self.assertEqual((unit.status, unit.current_reservation), ("Reserved", result["reservation"]))
		with as_user(SALES_USER):
			form = get_form("Sidra Unit", unit.name)
			self.assertEqual([action["key"] for action in form["actions"]], ["cancel_reservation"])
			with self.assertRaises(frappe.ValidationError):  # no longer offered
				run_action("Sidra Unit", unit.name, "reserve_unit", {"customer": BUYER}, str(unit.modified))
			reservation = frappe.get_doc("Sidra Reservation", result["reservation"])
			res_form = get_form("Sidra Reservation", reservation.name)
			self.assertFalse(res_form["permissions"]["write"])
			run_action(
				"Sidra Reservation", reservation.name, "cancel_reservation", {}, str(reservation.modified)
			)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Available")
		self.assertEqual(frappe.db.get_value("Sidra Reservation", reservation.name, "status"), "Cancelled")

	def test_reservations_are_not_created_or_edited_by_form(self):
		with as_user(SALES_MANAGER):
			with self.assertRaises(frappe.ValidationError):
				get_form("Sidra Reservation")
			with self.assertRaises(frappe.ValidationError):
				save_form("Sidra Reservation", {"unit": "x"})

	def test_unpriced_unit_warns_before_reserving(self):
		created = self.create_unit(cash_price=0)
		with as_user(SALES_USER):
			action = get_form("Sidra Unit", created["name"])["actions"][0]
		self.assertEqual(action["key"], "reserve_unit")
		self.assertIn("no positive asking price", action["confirm"])

	def test_kyc_verify_is_offered_to_the_manager_with_a_scan(self):
		customer = ensure_customer(unique("_Test KYC Customer"))
		values = {
			"customer": customer,
			"id_type": frappe.get_meta("Sidra Customer KYC").get_field("id_type").options.split("\n")[-1],
			"id_number": unique("ID"),
			"phone": "+252634111111",
			"address": "Hargeisa",
		}
		with as_user(SALES_USER):
			created = save_form("Sidra Customer KYC", values)
		doc = frappe.get_doc("Sidra Customer KYC", created["name"])
		with as_user(SALES_MANAGER):
			self.assertEqual(get_form("Sidra Customer KYC", doc.name)["actions"], [])  # no scan yet
		url = private_file(attached_to=doc, field="id_document")
		with as_user(SALES_USER):
			created = save_form(
				"Sidra Customer KYC",
				{"id_document": url},
				name=doc.name,
				expected_modified=created["modified"],
			)
			self.assertEqual(get_form("Sidra Customer KYC", doc.name)["actions"], [])  # not a manager
		with as_user(OTHER_SALES_MANAGER):  # a manager who can read customers, as on the real site
			self.assertEqual(
				[a["key"] for a in get_form("Sidra Customer KYC", doc.name)["actions"]], ["verify_kyc"]
			)
			run_action("Sidra Customer KYC", doc.name, "verify_kyc", {}, created["modified"])
		self.assertEqual(frappe.db.get_value("Sidra Customer KYC", doc.name, "status"), "Verified")
