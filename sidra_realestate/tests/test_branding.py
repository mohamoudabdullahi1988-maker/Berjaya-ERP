# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""White-label branding and navigation (sidra_realestate/branding.py; Mohamoud, 7 Nov 2026)."""

import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.www import login as login_page

from sidra_realestate.branding import (
	APP_ICON,
	BRAND_NAME,
	COMPANY_LOGO,
	HIDDEN_MODULES,
	LOGO,
	MODULE_PROFILE,
	apply_branding,
)
from sidra_realestate.tests.helpers import as_user, ensure_base_records, ensure_company

CLIENT_COMPANY = "Sidra Homes"


class TestBranding(IntegrationTestCase):
	def test_brand_name_and_logo(self):
		apply_branding()
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), BRAND_NAME)
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), LOGO)
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), LOGO)

	def test_product_name_has_one_source(self):
		"""G18: the software is Berjaya, read from branding.py by hooks and the apps screen."""
		self.assertEqual(BRAND_NAME, "Berjaya")
		self.assertEqual(frappe.get_hooks("app_title", app_name="sidra_realestate"), [BRAND_NAME])
		self.assertEqual(frappe.get_hooks("app_logo_url", app_name="sidra_realestate"), [LOGO])
		tile = frappe.get_hooks("add_to_apps_screen", app_name="sidra_realestate")[0]
		self.assertEqual((tile["title"], tile["logo"]), (BRAND_NAME, APP_ICON))
		self.assertEqual(tile["name"], "sidra_realestate")  # the identifier is unchanged
		self.assertEqual(tile["route"], "/sidra")

	def test_login_page_and_app_title_render_the_product_name(self):
		apply_branding()
		self.assertEqual(frappe.get_website_settings("app_name"), BRAND_NAME)
		self.assertEqual(frappe.get_system_settings("app_name"), BRAND_NAME)
		# The login page's own context: its name and the logo it shows (frappe/www/login.py).
		context = frappe._dict()
		with as_user("Guest"), patch.object(frappe.local, "request", frappe._dict(args={}), create=True):
			login_page.get_context(context)
		self.assertEqual(context["app_name"], BRAND_NAME)
		self.assertEqual(context["logo"], LOGO)

	def test_sign_in_page_loads_the_brand_stylesheet(self):
		"""G20: the sign-in page takes the Berjaya look from one stylesheet scoped to that page."""
		sheets = frappe.get_hooks("web_include_css", app_name="sidra_realestate")
		self.assertEqual(sheets, ["/assets/sidra_realestate/css/berjaya-login.css"])
		path = frappe.get_app_path("sidra_realestate", "public", "css", "berjaya-login.css")
		self.assertTrue(os.path.exists(path))
		with open(path) as handle:
			rules = [line for line in handle.read().split("\n") if line.rstrip().endswith(("{", ","))]
		# Every selector is scoped to the login page, so no other website page is restyled.
		unscoped = [r for r in rules if not r.startswith(("body[data-path='login']", "@media", "\t"))]
		self.assertEqual(unscoped, [])
		for image in (LOGO, APP_ICON):
			self.assertTrue(
				os.path.exists(
					frappe.get_app_path("sidra_realestate", "public", "images", image.rsplit("/", 1)[1])
				)
			)

	def test_earlier_product_branding_is_replaced(self):
		"""A site branded "Sidra Homes" by this app before G18 is rebranded on migrate."""
		old_logo = "/assets/sidra_realestate/images/sidra-logo.png"
		frappe.db.set_single_value("System Settings", "app_name", "Sidra Homes")
		frappe.db.set_single_value("Website Settings", "app_name", "Sidra Homes")
		frappe.db.set_single_value("Website Settings", "footer_powered", "Sidra Homes")
		frappe.db.set_single_value("Navbar Settings", "app_logo", old_logo)
		apply_branding()
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), BRAND_NAME)
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_name"), BRAND_NAME)
		self.assertEqual(frappe.db.get_single_value("Website Settings", "footer_powered"), BRAND_NAME)
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), LOGO)

	def test_company_keeps_the_client_name(self):
		"""G19: branding never renames, merges or creates a Company."""
		ensure_base_records()
		ensure_company(CLIENT_COMPANY, "SH")
		companies = sorted(frappe.get_all("Company", pluck="name"))
		apply_branding()
		self.assertEqual(sorted(frappe.get_all("Company", pluck="name")), companies)
		self.assertEqual(frappe.db.get_value("Company", CLIENT_COMPANY, "company_name"), CLIENT_COMPANY)
		self.assertFalse(frappe.db.exists("Company", BRAND_NAME))

	def test_company_logo_stays_on_the_print_formats(self):
		self.assertNotEqual(COMPANY_LOGO, LOGO)
		for path in (COMPANY_LOGO, LOGO, APP_ICON):
			relative = path.removeprefix("/assets/sidra_realestate/")
			self.assertTrue(
				os.path.exists(os.path.join(frappe.get_app_path("sidra_realestate"), "public", relative)),
				path,
			)
		for name in ("Sidra Sale Contract", "Sidra Sale Quotation", "Sidra Construction Quotation"):
			html = frappe.db.get_value("Print Format", name, "html")
			self.assertIn("sidra-logo.png", html, name)
			self.assertNotIn("erjaya", html, name)

	def test_staff_page_shows_the_product_name(self):
		path = os.path.join(frappe.get_app_path("sidra_realestate"), "public", "staff", "index.html")
		with open(path, encoding="utf-8") as fh:
			html = fh.read()
		self.assertIn(f"<title>{BRAND_NAME} · Staff</title>", html)
		self.assertIn(f">{BRAND_NAME.upper()}<", html)
		self.assertNotIn("Sidra Homes", html)
		self.assertNotIn("SIDRA", html)

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
