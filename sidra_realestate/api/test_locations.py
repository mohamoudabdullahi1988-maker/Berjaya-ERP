# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Location API with real Sidra roles (API-CONTRACT.md "Backend integration tests still required")."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api import locations
from sidra_realestate.tests.helpers import (
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_scheme,
	make_unit,
	unique,
)


class TestLocations(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.scheme = make_scheme("_TEST-LOC")

	def unit(self):
		return make_unit(unique("_T-LOC"), self.scheme)

	def test_set_get_and_kml(self):
		unit = self.unit()
		before = frappe.db.get_value("Sidra Unit", unit.name, ["status", "cash_price"], as_dict=True)
		with as_user(SALES_MANAGER):
			current = locations.get_location("Sidra Unit", unit.name)
			self.assertEqual(
				(current["latitude"], current["configured"], current["can_write"]), (None, True, True)
			)
			saved = locations.set_location("Sidra Unit", unit.name, "9.5616", "44.0650", current["modified"])
		self.assertEqual((saved["latitude"], saved["longitude"]), (9.5616, 44.065))  # order kept
		self.assertIn("google.com/maps", saved["links"]["maps"])
		reopened = locations.get_location("Sidra Unit", unit.name)
		self.assertEqual((reopened["latitude"], reopened["longitude"]), (9.5616, 44.065))
		after = frappe.db.get_value("Sidra Unit", unit.name, ["status", "cash_price"], as_dict=True)
		self.assertEqual(after, before)  # no business field touched

		locations.export_kml("Sidra Unit", unit.name)
		self.assertEqual(frappe.response["type"], "download")
		self.assertIn(b"44.065,9.5616,0", frappe.response["filecontent"])

	def test_stale_edit_refused(self):
		unit = self.unit()
		old = locations.get_location("Sidra Unit", unit.name)["modified"]
		locations.set_location("Sidra Unit", unit.name, 9.5, 44.0, old)
		with self.assertRaises(frappe.TimestampMismatchError):
			locations.set_location("Sidra Unit", unit.name, 9.6, 44.1, old)

	def test_invalid_coordinates_and_doctype(self):
		unit = self.unit()
		modified = locations.get_location("Sidra Unit", unit.name)["modified"]
		for lat, lng in ((91, 0), (0, 181), ("x", 0), ("", 0)):
			with self.subTest(lat=lat, lng=lng), self.assertRaises(frappe.ValidationError):
				locations.set_location("Sidra Unit", unit.name, lat, lng, modified)
		with self.assertRaises(frappe.PermissionError):
			locations.get_location("Sidra Sale Contract", "anything")

	def test_permissions(self):
		unit = self.unit()
		modified = locations.get_location("Sidra Unit", unit.name)["modified"]
		with as_user(SALES_USER):  # can read units, cannot write them
			self.assertFalse(locations.get_location("Sidra Unit", unit.name)["can_write"])
			with self.assertRaises(frappe.PermissionError):
				locations.set_location("Sidra Unit", unit.name, 9.5, 44.0, modified)
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			locations.get_location("Sidra Unit", unit.name)
