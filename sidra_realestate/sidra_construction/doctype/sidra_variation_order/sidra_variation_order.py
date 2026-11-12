# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Variation Order (CON-06; SRS v2.0 §3.1, §4.1; docs/CONSTRUCTION-CONTROLS_v0.1.md).

- An Addition raises and an Omission lowers the job's contract value; amounts are entered positive.
- Approval (submit) needs the client's approval recorded: who, when, and their signed approval
  as a private file on this record.
- A second person approves: the user who raised the order cannot submit it (SRS v1.6 §2).
  Sidra Project Manager or Sidra General Manager approve.
- The job must be contracted and carry its original contract value; the result cannot go below zero.
- The job's Approved Variations and Current Contract Value are recalculated from submitted orders.
- Recorded only: no Sales Order amendment, invoice or posting (CLAUDE.md rule 3).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from sidra_realestate.services.construction import (
	VARIATION_STATUSES,
	ConstructionRuleError,
	contract_value_after,
	signed_variation,
)
from sidra_realestate.services.construction_jobs import (
	approved_variation_amounts,
	check_job_access,
	check_own_private_file,
	lock_job,
	refresh_variation_totals,
	set_job_fields,
)


def rule(fn, *args):
	try:
		return fn(*args)
	except ConstructionRuleError as e:
		frappe.throw(str(e))


class SidraVariationOrder(Document):
	def validate(self):
		# Approvers (submit) need only read access to the job; drafts need write.
		check_job_access(self, "write" if self.docstatus == 0 else "read")
		set_job_fields(self)
		if self.variation_type:
			self.signed_amount = flt(rule(signed_variation, self.variation_type, self.amount), 2)
		if not (self.description or "").strip():
			frappe.throw(_("Describe the change"))
		if self.boq_revision:
			rev = frappe.db.get_value(
				"Sidra BOQ Revision", self.boq_revision, ["job", "docstatus"], as_dict=True
			)
			if not rev or rev.job != self.job or rev.docstatus != 1:
				frappe.throw(
					_("BOQ revision {0} is not an approved revision of job {1}").format(
						self.boq_revision, self.job
					)
				)
		if self.client_approved_on and getdate(self.client_approved_on) > getdate(today()):
			frappe.throw(_("The client approval date cannot be in the future"))

	def before_submit(self):
		if frappe.session.user == self.owner:
			frappe.throw(
				_(
					"A variation order is approved by a second person: {0} raised it and cannot approve it"
				).format(self.owner),
				frappe.PermissionError,
				title=_("Second approver needed"),
			)
		if not (self.client_approved_by or "").strip() or not self.client_approved_on:
			frappe.throw(_("Record who approved the variation for the client and when"))
		if not self.client_approval_document:
			frappe.throw(_("Attach the client's signed approval"))
		check_own_private_file(self, "client_approval_document", _("signed client approval"))

		job = lock_job(self.job)
		if job.status not in VARIATION_STATUSES:
			frappe.throw(
				_("Job {0} is {1}; variations are approved only on a contracted job ({2})").format(
					job.name, job.status, ", ".join(VARIATION_STATUSES)
				)
			)
		approved = approved_variation_amounts(self.job, exclude=self.name)
		self.contract_value_before = flt(rule(contract_value_after, job.contract_value, approved), 2)
		self.contract_value_after = flt(
			rule(contract_value_after, job.contract_value, approved, self.signed_amount), 2
		)
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()

	def on_submit(self):
		refresh_variation_totals(self.job)

	def before_cancel(self):
		job = lock_job(self.job)
		# Removing this order must not leave the other approved orders below zero.
		rule(
			contract_value_after, job.contract_value, approved_variation_amounts(self.job, exclude=self.name)
		)

	def on_cancel(self):
		refresh_variation_totals(self.job)
