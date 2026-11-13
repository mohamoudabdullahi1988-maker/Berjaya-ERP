# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The Sidra front page at /sidra: staff only, doors by permission, permission-filtered counts."""

import importlib.util
import os

import frappe
from frappe.apps import get_route
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response

from sidra_realestate.api.shell import build_shell
from sidra_realestate.branding import BRAND_NAME
from sidra_realestate.tests.helpers import (
	OUTSIDER,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_job,
)


def _page_module():
	path = os.path.join(frappe.get_app_path("sidra_realestate"), "www", "sidra", "index.py")
	spec = importlib.util.spec_from_file_location("sidra_shell_page", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _doors(shell):
	return {door["key"] for door in shell["doors"]}


def _step(shell, service, label):
	steps = next(s for s in shell["services"] if s["key"] == service)["steps"]
	return next(step for step in steps if step["label"] == label)


class TestShell(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_page_renders_for_staff_without_platform_names(self):
		with as_user(SALES_MANAGER):
			response = get_response("sidra")
		self.assertEqual(response.status_code, 200)
		html = response.get_data(as_text=True)
		self.assertIn("/assets/sidra_realestate/shell/shell.css", html)
		self.assertIn("Real Estate Sales", html)
		self.assertIn(f"<title>{BRAND_NAME}</title>", html)
		self.assertIn(f"<span>{BRAND_NAME}</span>", html)
		self.assertNotIn("Sidra Homes", html)
		self.assertIn('href="/sidra-staff/"', html)
		self.assertIn('id="real-estate"', html)
		for platform in ("ERPNext", "Frappe"):
			self.assertNotIn(platform, html)

	def test_guest_goes_to_login_and_other_people_to_their_desk(self):
		page = _page_module()
		with as_user("Guest"), self.assertRaises(frappe.Redirect):
			page.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=%2Fsidra")
		with as_user(OUTSIDER), self.assertRaises(frappe.Redirect):
			page.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/desk")

	def test_doors_follow_permissions(self):
		with as_user(SALES_USER):
			sales = _doors(build_shell())
		self.assertIn("dashboard", sales)
		self.assertIn("real-estate", sales)
		self.assertNotIn("financials", sales, "no ledger access, so no Financials door")
		with as_user(PROJECT_MANAGER):
			construction = _doors(build_shell())
		self.assertIn("construction", construction)
		self.assertNotIn("financials", construction)
		with as_user("Administrator"):
			shell = build_shell()
		self.assertLessEqual({"dashboard", "financials", "real-estate", "construction"}, _doors(shell))
		self.assertIn("General Ledger", [report["label"] for report in shell["reports"]])

	def test_counts_are_live_and_link_to_the_filtered_list(self):
		with as_user(PROJECT_MANAGER):
			before = _step(build_shell(), "construction", "Enquiries")
		job = make_job()
		self.assertEqual(job.status, "Enquiry")
		with as_user(PROJECT_MANAGER):
			after = _step(build_shell(), "construction", "Enquiries")
		self.assertEqual(after["count"], before["count"] + 1)
		self.assertEqual(after["href"], "/desk/sidra-construction-job?status=Enquiry")

	def test_a_step_the_user_cannot_read_is_left_out_not_zero(self):
		with as_user(PROJECT_MANAGER):
			shell = build_shell()
		self.assertFalse(frappe.has_permission("Sidra Customer KYC", "read", user=PROJECT_MANAGER))
		labels = [row["label"] for service in shell["services"] for row in service["attention"]]
		self.assertNotIn("Buyer KYC to verify", labels)

	def test_signing_in_lands_on_the_front_page(self):
		self.assertEqual(get_route("sidra_realestate"), "/sidra")
		hook = frappe.get_hooks("add_to_apps_screen", app_name="sidra_realestate")[0]
		self.assertEqual(hook["desk_route"], "/desk/sidra-sale-contract")
		self.assertTrue(frappe.db.get_single_value("System Settings", "default_app"))
