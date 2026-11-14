# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The Sidra front page at /sidra: staff only, doors by permission, permission-filtered counts."""

import importlib.util
import os

import frappe
from frappe.apps import get_route
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.shell import build_shell
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

	def test_old_front_page_sends_everyone_on(self):
		"""Decision G21: /sidra is retired. Staff go to /berjaya, guests sign in first, others to Desk."""
		page = _page_module()
		for user, target in (
			("Guest", "/login?redirect-to=%2Fberjaya"),
			(SALES_MANAGER, "/berjaya"),
			(OUTSIDER, "/desk"),
		):
			with as_user(user), self.assertRaises(frappe.Redirect) as raised:
				page.get_context(frappe._dict())
			self.assertEqual(frappe.local.flags.redirect_location, target, user)
			self.assertEqual(raised.exception.http_status_code, 302, user)

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

	def test_signing_in_lands_on_berjaya(self):
		self.assertEqual(get_route("sidra_realestate"), "/berjaya")  # decision G21
		hook = frappe.get_hooks("add_to_apps_screen", app_name="sidra_realestate")[0]
		self.assertEqual(hook["desk_route"], "/desk/sidra-sale-contract")
		self.assertTrue(frappe.db.get_single_value("System Settings", "default_app"))
