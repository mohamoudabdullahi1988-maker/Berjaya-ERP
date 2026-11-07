# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The /sidra-staff/ page: staff only, CSRF token injected, assets from the app."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response

from sidra_realestate.tests.helpers import OUTSIDER, SALES_MANAGER, as_user, ensure_base_records


class TestStaffPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def render(self, user):
		with as_user(user):
			frappe.local.session.data.csrf_token = "test-csrf-token"
			return get_response("sidra-staff")

	def test_staff_page(self):
		response = self.render(SALES_MANAGER)
		self.assertEqual(response.status_code, 200)
		html = response.get_data(as_text=True)
		self.assertIn('<base href="/assets/sidra_realestate/staff/">', html)
		self.assertIn('frappe.csrf_token = "test-csrf-token"', html)
		self.assertIn("sidra_realestate.api.staff_dashboard.get_dashboard", html)
		self.assertIn('<script src="./config.js"></script>', html)
		self.assertNotIn("&lt;script", html)  # not escaped

	def test_outsider_refused_and_guest_redirected(self):
		self.assertNotEqual(self.render(OUTSIDER).status_code, 200)
		self.assertIn(self.render("Guest").status_code, (301, 302, 303))
