# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""G32: identity access to one buyer's record only with the General Manager's approval."""

import frappe
import frappe.share
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.sidra_sales.doctype.sidra_kyc_access_request.sidra_kyc_access_request import (
	approve,
	expire_access,
	refuse,
	revoke,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	GENERAL_MANAGER,
	INSPECTOR,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
)

KYC = "Sidra Customer KYC"
REQUEST = "Sidra KYC Access Request"


class TestSidraKYCAccessRequest(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.kyc = frappe.db.get_value(KYC, {"customer": BUYER}, "name")

	def setUp(self):
		frappe.db.delete(REQUEST)
		frappe.db.delete("DocShare", {"share_doctype": KYC})

	def request(self, user=INSPECTOR, by=SALES_MANAGER):
		with as_user(by):
			return frappe.get_doc(
				{"doctype": REQUEST, "kyc": self.kyc, "user": user, "reason": "_Test title file check"}
			).insert()

	def can_read(self, user, ptype="read"):
		with as_user(user):
			return bool(frappe.has_permission(KYC, ptype, doc=self.kyc))

	def share(self):
		return frappe.db.get_value(
			"DocShare",
			{"share_doctype": KYC, "share_name": self.kyc, "user": INSPECTOR},
			["read", "write", "share", "everyone"],
			as_dict=True,
		)

	def test_a_sales_manager_or_the_gm_asks(self):
		for by in (SALES_MANAGER, GENERAL_MANAGER):
			with self.subTest(by=by):
				doc = self.request(by=by)
				self.assertEqual((doc.status, doc.requested_by, doc.customer), ("Pending", by, BUYER))
				frappe.db.delete(REQUEST)
		for by in (SALES_USER, PROJECT_MANAGER, INSPECTOR):
			with self.subTest(by=by), self.assertRaises(frappe.PermissionError):
				self.request(by=by)

	def test_no_request_for_someone_who_already_reads_it_or_twice(self):
		with self.assertRaises(frappe.ValidationError):
			self.request(user=SALES_USER)
		self.request()
		with self.assertRaises(frappe.ValidationError):
			self.request()

	def test_the_requester_cannot_decide(self):
		doc = self.request()
		doc.status = "Approved"
		doc.valid_until = add_days(today(), 90)
		with as_user(SALES_MANAGER):
			doc.save()
			with self.assertRaises(frappe.PermissionError):
				approve(doc.name)
		doc.reload()
		self.assertEqual((doc.status, doc.valid_until), ("Pending", None))
		self.assertFalse(self.can_read(INSPECTOR))

	def test_gm_approval_gives_read_only_access_until_the_day(self):
		doc = self.request()
		self.assertFalse(self.can_read(INSPECTOR))
		with as_user(GENERAL_MANAGER):
			result = approve(doc.name)
		self.assertEqual(result["valid_until"], str(getdate(add_days(today(), 30))))
		self.assertTrue(self.can_read(INSPECTOR))
		self.assertFalse(self.can_read(INSPECTOR, "write"))
		share = self.share()
		self.assertEqual((share.read, share.write, share.share, share.everyone), (1, 0, 0, 0))
		doc.reload()
		self.assertEqual((doc.status, doc.decided_by), ("Approved", GENERAL_MANAGER))

	def test_no_access_into_the_past(self):
		doc = self.request()
		with as_user(GENERAL_MANAGER), self.assertRaises(frappe.ValidationError):
			approve(doc.name, valid_until=add_days(today(), -1))

	def test_approval_cannot_be_borrowed(self):
		doc = self.request()
		with as_user(GENERAL_MANAGER):
			approve(doc.name)
		attempts = (
			{"user": PROJECT_MANAGER, "read": 1},  # someone else
			{"user": INSPECTOR, "read": 1, "write": 1},  # more than read
			{"user": INSPECTOR, "read": 1, "share": 1},  # re-share right
			{"everyone": 1, "read": 1},
		)
		for kwargs in attempts:
			with self.subTest(**kwargs), self.assertRaises(frappe.PermissionError):
				frappe.share.add_docshare(
					KYC,
					self.kyc,
					flags={"ignore_share_permission": True, "sidra_kyc_access_request": doc.name},
					**kwargs,
				)
		# Desk's Share button carries no approval.
		with self.assertRaises(frappe.PermissionError):
			frappe.share.add_docshare(
				KYC, self.kyc, user=PROJECT_MANAGER, read=1, flags={"ignore_share_permission": True}
			)
		self.assertFalse(self.can_read(PROJECT_MANAGER))

	def test_refusal_needs_a_reason(self):
		doc = self.request()
		with as_user(GENERAL_MANAGER):
			with self.assertRaises(frappe.ValidationError):
				refuse(doc.name)
			refuse(doc.name, note="_Test not needed")
			with self.assertRaises(frappe.ValidationError):
				approve(doc.name)
		self.assertFalse(self.can_read(INSPECTOR))

	def test_revoke_ends_access(self):
		doc = self.request()
		with as_user(GENERAL_MANAGER):
			approve(doc.name)
			revoke(doc.name, note="_Test done")
		self.assertFalse(self.can_read(INSPECTOR))
		self.assertFalse(self.share())
		doc.reload()
		self.assertEqual(doc.status, "Revoked")
		self.assertTrue(doc.ended_on)
		# A new request can follow.
		self.request()

	def test_access_expires_after_the_last_day(self):
		doc = self.request()
		with as_user(GENERAL_MANAGER):
			approve(doc.name, valid_until=today())
		expire_access()
		self.assertTrue(self.can_read(INSPECTOR))
		frappe.db.set_value(REQUEST, doc.name, "valid_until", add_days(today(), -1))
		expire_access()
		self.assertFalse(self.can_read(INSPECTOR))
		self.assertEqual(frappe.db.get_value(REQUEST, doc.name, "status"), "Expired")
