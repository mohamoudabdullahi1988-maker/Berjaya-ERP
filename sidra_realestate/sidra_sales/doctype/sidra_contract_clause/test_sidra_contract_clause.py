# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Clause library approval rules (SAL-20; issue #8)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import GENERAL_MANAGER, SYSTEM_ONLY, as_user, ensure_base_records, unique

IGNORE_TEST_RECORD_DEPENDENCIES = ["User"]


class TestSidraContractClause(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def clause(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Sidra Contract Clause",
				"clause_code": unique("_T-CL"),
				"title": "_Test clause",
				"text_so": "Qoraal Soomaali ah.",
				"text_en": "English text.",
				**values,
			}
		).insert(ignore_permissions=True)

	def test_general_manager_approves(self):
		doc = self.clause()
		with as_user(GENERAL_MANAGER):
			doc = frappe.get_doc("Sidra Contract Clause", doc.name)
			doc.approved = 1
			doc.save()
		self.assertEqual(
			frappe.db.get_value("Sidra Contract Clause", doc.name, ["approved", "approved_by"]),
			(1, GENERAL_MANAGER),
		)

	def test_others_cannot_approve(self):
		doc = self.clause()
		with as_user(SYSTEM_ONLY), self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("Sidra Contract Clause", doc.name)
			doc.approved = 1
			doc.save()

	def test_approval_needs_both_languages(self):
		with self.assertRaises(frappe.ValidationError):
			self.clause(text_en="", approved=1)
		with self.assertRaises(frappe.ValidationError):
			self.clause(text_so="  ", approved=1)

	def test_edit_by_non_approver_clears_approval(self):
		doc = self.clause(approved=1)
		with as_user(SYSTEM_ONLY):
			doc = frappe.get_doc("Sidra Contract Clause", doc.name)
			doc.text_en = "Reworded."
			doc.save()
		self.assertEqual(
			frappe.db.get_value("Sidra Contract Clause", doc.name, ["approved", "approved_by"]), (0, None)
		)

	def test_title_edit_keeps_approval(self):
		doc = self.clause(approved=1)
		with as_user(SYSTEM_ONLY):
			doc = frappe.get_doc("Sidra Contract Clause", doc.name)
			doc.title = "_Test clause renamed"
			doc.save()
		self.assertEqual(frappe.db.get_value("Sidra Contract Clause", doc.name, "approved"), 1)

	def test_clause_in_use_cannot_be_deleted(self):
		doc = self.clause()
		frappe.get_doc(
			{
				"doctype": "Sidra Contract Profile",
				"profile_name": unique("_Test Clause Holder"),
				"installments": 10,
				"due_day": 5,
				"title_deadline_days": 20,
				"clauses": [{"clause": doc.name}],
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Sidra Contract Clause", doc.name, ignore_permissions=True)
