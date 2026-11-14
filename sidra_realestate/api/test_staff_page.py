# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The retired /sidra-staff/ page: it redirects staff to /berjaya (decision G21)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import OUTSIDER, SALES_MANAGER, as_user, ensure_base_records


class TestStaffPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_staff_go_to_berjaya_and_outsiders_are_refused(self):
		"""Decision G21: /sidra-staff/ is retired and sends staff to /berjaya."""
		page = _page_module()
		with as_user(SALES_MANAGER), self.assertRaises(frappe.Redirect) as raised:
			page.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/berjaya")
		self.assertEqual(raised.exception.http_status_code, 302)
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			page.get_context(frappe._dict())
		with as_user("Guest"), self.assertRaises(frappe.Redirect) as raised:
			page.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=%2Fberjaya")
		self.assertEqual(raised.exception.http_status_code, 302)


def _page_module():
	"""The www page module (its folder name has a hyphen, so it is loaded by path)."""
	import importlib.util
	import os

	path = os.path.join(frappe.get_app_path("sidra_realestate"), "www", "sidra-staff", "index.py")
	spec = importlib.util.spec_from_file_location("sidra_staff_page", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module
