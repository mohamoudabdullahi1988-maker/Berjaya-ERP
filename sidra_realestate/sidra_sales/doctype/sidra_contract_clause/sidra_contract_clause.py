# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Contract clause library (SAL-20). Wording comes from Sidra; see issue #8.

Only the General Manager approves wording. Anyone else who edits the wording clears
the approval. Contracts keep their own copy of the wording (Sidra Contract Clause Line),
so later edits never reach a saved contract.
"""

import frappe
from frappe import _
from frappe.model.document import Document

APPROVER = "Sidra General Manager"


class SidraContractClause(Document):
	def validate(self):
		before = self.get_doc_before_save()
		is_approver = APPROVER in frappe.get_roles()
		wording_changed = before is not None and (
			(before.text_so or "") != (self.text_so or "") or (before.text_en or "") != (self.text_en or "")
		)
		newly_approved = self.approved and (before is None or not before.approved)

		if self.approved and not is_approver and (newly_approved or wording_changed):
			if newly_approved:
				frappe.throw(_("Only the General Manager can approve clause wording"), frappe.PermissionError)
			self.approved = 0  # someone else edited approved wording: it needs approval again

		if self.approved and not ((self.text_so or "").strip() and (self.text_en or "").strip()):
			frappe.throw(_("An approved clause needs both Somali and English text"))

		if not self.approved:
			self.approved_by = None
		elif newly_approved or wording_changed:
			self.approved_by = frappe.session.user

	def on_trash(self):
		for doctype in ("Sidra Profile Clause", "Sidra Contract Clause Line"):
			if frappe.db.exists(doctype, {"clause": self.name}):
				frappe.throw(_("Clause {0} is in use; set it inactive instead").format(self.name))
