# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G36: staff use ERPNext Desk with normal Frappe permissions; G32 still holds there."""

import frappe
import frappe.share
from frappe.desk.form.assign_to import add as assign
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import (
	BUYER,
	GENERAL_MANAGER,
	INSPECTOR,
	OUTSIDER,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
)

STAFF = (SALES_USER, SALES_MANAGER, PROJECT_MANAGER, GENERAL_MANAGER, INSPECTOR)


class TestDeskAccess(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.kyc = frappe.db.get_value("Sidra Customer KYC", {"customer": BUYER}, "name")

	def test_desk_is_not_redirected(self):
		self.assertNotIn("sidra_realestate.cutover.before_request", frappe.get_hooks("before_request"))

	def test_staff_are_desk_users(self):
		for user in STAFF:
			with self.subTest(user=user):
				self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")
				roles = [r for r in frappe.get_roles(user) if r.startswith("Sidra ")]
				self.assertTrue(roles)
				self.assertTrue(
					frappe.get_all("Role", filters={"name": ["in", roles], "desk_access": 1}, limit=1)
				)

	def test_restricted_records_stay_restricted(self):
		# Project risks: Project Managers, the General Manager and Inspectors only (G26).
		for user, allowed in (
			(PROJECT_MANAGER, True),
			(INSPECTOR, True),
			(SALES_USER, False),
			(OUTSIDER, False),
		):
			with self.subTest(user=user), as_user(user):
				self.assertEqual(bool(frappe.has_permission("Sidra Project Risk", "read")), allowed)
		# Buyer identity records: sales and the General Manager; never construction or outsiders.
		for user in (PROJECT_MANAGER, INSPECTOR, OUTSIDER):
			with self.subTest(user=user), as_user(user):
				self.assertFalse(frappe.has_permission("Sidra Customer KYC", "read", self.kyc))
		with as_user(OUTSIDER):
			self.assertFalse(frappe.has_permission("Sidra Sale Contract", "read"))

	def test_kyc_cannot_be_shared_from_desk(self):
		for kwargs in ({"user": PROJECT_MANAGER}, {"everyone": 1}):
			with self.subTest(**kwargs), self.assertRaises(frappe.PermissionError):
				frappe.share.add_docshare(
					"Sidra Customer KYC", self.kyc, read=1, flags={"ignore_share_permission": True}, **kwargs
				)
		self.assertFalse(
			frappe.db.exists("DocShare", {"share_doctype": "Sidra Customer KYC", "share_name": self.kyc})
		)

	def test_kyc_assignment_does_not_open_it(self):
		# Frappe shares an assigned record with an assignee who cannot read it; that share is refused.
		frappe.db.savepoint("kyc_assignment")
		with self.assertRaises(frappe.PermissionError):
			assign({"doctype": "Sidra Customer KYC", "name": self.kyc, "assign_to": [INSPECTOR]})
		frappe.db.rollback(save_point="kyc_assignment")
		with as_user(INSPECTOR):
			self.assertFalse(frappe.has_permission("Sidra Customer KYC", "read", self.kyc))

	def test_other_records_can_still_be_shared(self):
		share = frappe.share.add_docshare(
			"Customer", BUYER, user=PROJECT_MANAGER, read=1, flags={"ignore_share_permission": True}
		)
		self.assertTrue(share)
		frappe.share.remove("Customer", BUYER, PROJECT_MANAGER)
