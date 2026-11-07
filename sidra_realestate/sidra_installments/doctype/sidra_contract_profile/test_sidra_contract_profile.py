# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Contract profiles (INS-18; handover v1.0 §4.1; SRS v2.0 §1.4, §3.3; decision D4, issue #13)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.install import PROFILE_B_TITLE_DEADLINE_NOTE, ensure_contract_profiles
from sidra_realestate.patches.v0_3 import resolve_profile_b_title_deadline
from sidra_realestate.tests.helpers import (
	GENERAL_MANAGER,
	SYSTEM_ONLY,
	as_user,
	ensure_base_records,
	make_held_profile,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Sale Contract"]


class TestSidraContractProfile(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()

	def test_profile_a_values(self):
		a = frappe.get_doc("Sidra Contract Profile", "Profile A")
		expected = {
			"is_default": 1,
			"active": 1,
			"legal_hold": 0,
			"installments": 14,
			"due_day": 5,
			"grace_months": 0,
			"down_payment_type": "None",
			"markup_rate": 0,
			"penalty_type": "Per Day Capped",
			"penalty_per_day": 5,
			"penalty_monthly_cap": 150,
			"default_trigger_missed": 2,
			"refund_retention_type": "One Installment",
			"title_deadline_days": 20,
			"title_penalty_type": "Per Day",
			"title_penalty_amount": 5,
			"penalty_destination": "Pending Policy Sign-off",
		}
		self.assertEqual({k: a.get(k) for k in expected}, expected)

	def test_profile_b_values_d4(self):
		"""Fresh install: 20-day title deadline and no legal hold (D4, issue #13)."""
		b = frappe.get_doc("Sidra Contract Profile", "Profile B")
		expected = {
			"is_default": 0,
			"legal_hold": 0,
			"installments": 24,
			"due_day": 10,
			"grace_months": 3,
			"down_payment_type": "Fixed",
			"down_payment_value": 3000,
			"penalty_type": "Fixed After Notice",
			"penalty_fixed_amount": 100,
			"notice_days": 15,
			"default_trigger_missed": 0,
			"title_deadline_days": 20,  # D4: the 14 in Contract B is a typo
			"title_penalty_type": "Per Month",
			"title_penalty_amount": 220,
			"title_refund_after_days": 90,
			"title_refund_compensation_pct": 10,
		}
		self.assertEqual({k: b.get(k) for k in expected}, expected)
		self.assertFalse(b.legal_hold_reason)
		self.assertEqual(b.title_deadline_note, PROFILE_B_TITLE_DEADLINE_NOTE)

	# ------------------------------------------------------------ D4 patch
	def set_profile_b(self, **values):
		frappe.db.set_value("Sidra Contract Profile", "Profile B", values)

	def profile_b_state(self):
		return frappe.db.get_value(
			"Sidra Contract Profile",
			"Profile B",
			["legal_hold", "title_deadline_days", "legal_hold_reason", "title_deadline_note"],
			as_dict=True,
		)

	def d4_comments(self):
		return frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Sidra Contract Profile",
				"reference_name": "Profile B",
				"comment_type": "Comment",
				"content": ("like", "%Decision D4%"),
			},
			pluck="name",
		)

	def restore_profile_b(self):
		self.set_profile_b(
			legal_hold=0,
			legal_hold_reason=None,
			title_deadline_days=20,
			title_deadline_note=PROFILE_B_TITLE_DEADLINE_NOTE,
		)
		for name in self.d4_comments():
			frappe.delete_doc("Comment", name, ignore_permissions=True, force=True)

	def test_patch_resolves_seeded_hold_and_is_safe_twice(self):
		self.addCleanup(self.restore_profile_b)
		self.set_profile_b(
			legal_hold=1,
			legal_hold_reason="Unresolved: 20 days (clause 4) or 14 days (clause 6).",
			title_deadline_days=0,
			title_deadline_note="Unresolved",
		)
		before = len(self.d4_comments())

		resolve_profile_b_title_deadline.execute()
		state = self.profile_b_state()
		self.assertEqual((state.legal_hold, state.title_deadline_days), (0, 20))
		self.assertFalse(state.legal_hold_reason)
		self.assertEqual(state.title_deadline_note, PROFILE_B_TITLE_DEADLINE_NOTE)
		self.assertEqual(len(self.d4_comments()), before + 1)

		resolve_profile_b_title_deadline.execute()  # second run: no change, no second comment
		self.assertEqual(self.profile_b_state(), state)
		self.assertEqual(len(self.d4_comments()), before + 1)

	def test_patch_leaves_profile_edited_by_management(self):
		self.addCleanup(self.restore_profile_b)
		for edited in (
			{"legal_hold": 1, "title_deadline_days": 14},
			{"legal_hold": 0, "title_deadline_days": 25},
		):
			with self.subTest(**edited):
				self.set_profile_b(legal_hold_reason="Set by management", **edited)
				before = len(self.d4_comments())
				resolve_profile_b_title_deadline.execute()
				state = self.profile_b_state()
				self.assertEqual(
					(state.legal_hold, state.title_deadline_days),
					(edited["legal_hold"], edited["title_deadline_days"]),
				)
				self.assertEqual(state.legal_hold_reason, "Set by management")
				self.assertEqual(len(self.d4_comments()), before)

	def test_seeding_does_not_overwrite(self):
		frappe.db.set_value("Sidra Contract Profile", "Profile A", "notice_days", 3)
		ensure_contract_profiles()
		self.assertEqual(frappe.db.get_value("Sidra Contract Profile", "Profile A", "notice_days"), 3)
		frappe.db.set_value("Sidra Contract Profile", "Profile A", "notice_days", 0)

	def test_only_one_default(self):
		doc = self.new_profile(is_default=1)
		self.assertEqual(frappe.db.get_value("Sidra Contract Profile", "Profile A", "is_default"), 0)
		self.assertEqual(frappe.db.get_value("Sidra Contract Profile", doc.name, "is_default"), 1)
		frappe.db.set_value("Sidra Contract Profile", "Profile A", "is_default", 1)
		frappe.db.set_value("Sidra Contract Profile", doc.name, "is_default", 0)

	def test_ranges(self):
		for field, value in (("due_day", 29), ("due_day", 0), ("installments", 61), ("grace_months", 13)):
			with self.subTest(field=field, value=value), self.assertRaises(frappe.ValidationError):
				self.new_profile(**{field: value})

	def test_down_payment_rules(self):
		with self.assertRaises(frappe.ValidationError):
			self.new_profile(down_payment_type="Fixed", down_payment_value=0)
		with self.assertRaises(frappe.ValidationError):
			self.new_profile(down_payment_type="Percent", down_payment_value=120)

	def test_title_deadline_required_unless_on_hold(self):
		with self.assertRaises(frappe.ValidationError):
			self.new_profile(title_deadline_days=0)
		self.assertTrue(self.new_profile(title_deadline_days=0, legal_hold=1, legal_hold_reason="pending"))

	def test_only_general_manager_lifts_legal_hold(self):
		held = make_held_profile()
		with as_user(SYSTEM_ONLY), self.assertRaises(frappe.PermissionError):
			b = frappe.get_doc("Sidra Contract Profile", held.name)
			b.legal_hold = 0
			b.save()
		self.assertEqual(frappe.db.get_value("Sidra Contract Profile", held.name, "legal_hold"), 1)

		doc = self.new_profile(legal_hold=1, legal_hold_reason="pending")
		with as_user(GENERAL_MANAGER):
			doc = frappe.get_doc("Sidra Contract Profile", doc.name)
			doc.legal_hold = 0
			doc.save()
		self.assertEqual(frappe.db.get_value("Sidra Contract Profile", doc.name, "legal_hold"), 0)

	def new_profile(self, **values):
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Contract Profile",
				"profile_name": unique("_Test Profile"),
				"installments": 12,
				"due_day": 5,
				"title_deadline_days": 20,
				**values,
			}
		)
		return doc.insert(ignore_permissions=True)
