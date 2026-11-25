"""Regional settings work on fresh sites and migrate existing demo records."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.patches.v0_4.set_somaliland_country import execute
from sidra_realestate.site_setup import REGIONAL, apply_regional_settings, ensure_country
from sidra_realestate.tests.helpers import ensure_base_records, ensure_company


class TestSiteSetup(IntegrationTestCase):
	def test_country_and_settings_are_repeatable(self):
		self.assertEqual(ensure_country(), "Somaliland")
		self.assertEqual(ensure_country(), "Somaliland")
		self.assertEqual(frappe.db.get_value("Country", "Somaliland", "code"), "so")
		self.assertEqual(apply_regional_settings(), REGIONAL)
		self.assertEqual(apply_regional_settings(), REGIONAL)

	def test_migration_updates_existing_links_and_keeps_other_countries(self):
		ensure_base_records()
		company = ensure_company("_Test Sidra Regional", "_TSR")
		other = ensure_company("_Test Sidra Regional Other", "_TSRO")
		frappe.db.set_value("Company", company, "country", "Somalia")
		frappe.db.set_value("Company", other, "country", "Germany")
		if not frappe.db.exists("Territory", "Somalia"):
			frappe.get_doc(
				{
					"doctype": "Territory",
					"territory_name": "Somalia",
					"parent_territory": "All Territories",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Address Template", "Somalia"):
			frappe.get_doc({"doctype": "Address Template", "country": "Somalia"}).insert(
				ignore_permissions=True
			)
		frappe.db.set_value("Customer", "_Test Buyer Amina", "territory", "Somalia")
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "_Test Sidra Regional",
				"address_type": "Billing",
				"address_line1": "_Test street",
				"city": "Hargeisa",
				"country": "Somalia",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("System Settings", "country", "Somalia")
		frappe.db.set_single_value("Global Defaults", "country", "Somalia")
		frappe.db.set_default("country", "Somalia")
		execute()
		execute()
		self.assertEqual(frappe.db.get_value("Company", company, "country"), "Somaliland")
		self.assertEqual(frappe.db.get_value("Address", address.name, "country"), "Somaliland")
		self.assertEqual(frappe.db.get_single_value("System Settings", "country"), "Somaliland")
		self.assertEqual(frappe.db.get_single_value("Global Defaults", "country"), "Somaliland")
		self.assertEqual(frappe.db.get_default("country"), "Somaliland")
		self.assertEqual(frappe.db.get_value("Company", other, "country"), "Germany")
		self.assertEqual(frappe.db.get_value("Customer", "_Test Buyer Amina", "territory"), "Somaliland")
		self.assertTrue(frappe.db.exists("Territory", "Somaliland"))
		self.assertFalse(frappe.db.exists("Territory", "Somalia"))
		self.assertTrue(frappe.db.exists("Address Template", "Somaliland"))
		self.assertFalse(frappe.db.exists("Address Template", "Somalia"))
