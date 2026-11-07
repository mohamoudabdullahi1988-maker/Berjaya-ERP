# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""White-label branding and navigation (sidra_realestate/branding.py; Mohamoud, 7 Nov 2026)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.branding import BRAND_NAME, HIDDEN_MODULES, LOGO, MODULE_PROFILE, apply_branding


class TestBranding(IntegrationTestCase):
	def test_brand_name_and_logo(self):
		apply_branding()
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), BRAND_NAME)
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), LOGO)
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), LOGO)

	def test_administrator_choice_is_kept(self):
		frappe.db.set_single_value("Website Settings", "app_name", "_Test Custom Name")
		self.addCleanup(frappe.db.set_single_value, "Website Settings", "app_name", BRAND_NAME)
		apply_branding()
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_name"), "_Test Custom Name")

	def test_unused_modules_hidden_for_staff(self):
		apply_branding()
		blocked = set(frappe.get_all("Block Module", filters={"parent": MODULE_PROFILE}, pluck="module"))
		self.assertTrue({"Manufacturing", "Stock", "Projects", "Buying"} <= blocked)
		self.assertTrue(blocked <= set(HIDDEN_MODULES))
		self.assertFalse({"Accounts", "Selling"} & blocked)

	def test_dock_and_sidebars_installed(self):
		self.assertTrue(frappe.db.exists("Dock", "sidra_realestate"))
		for name in ("Sidra Real Estate", "Sidra Construction"):
			self.assertTrue(frappe.db.exists("Sidebar", name), name)
		links = frappe.get_all(
			"Sidebar Item", filters={"parent": "Sidra Real Estate", "type": "Link"}, pluck="link_to"
		)
		self.assertIn("Sidra Sale Contract", links)
		self.assertIn("Sidra Unit", links)
