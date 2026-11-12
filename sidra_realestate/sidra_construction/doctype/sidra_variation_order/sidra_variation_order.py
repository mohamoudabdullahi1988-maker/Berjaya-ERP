# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Variation Order (CON-06; SRS v2.0 §3.1; decision G11; docs/CONSTRUCTION-CONTROLS_v0.2.md).

- Additions only: the amount (positive) raises the job's contract value.
- Approval (submit) needs the client's approval recorded: who, when, and their signed approval
  as a private file on this record.
- A second person approves: the user who raised the order cannot. Up to 1,000 a Sidra Project
  Manager or the Sidra General Manager approves; above 1,000 only the General Manager (G11).
  Cancelling an approved order follows the same rule.
- The job must have a contract approved from its quotation (CON-03) and be contracted.
- The job's Approved Variations, Current Contract Value and milestone amounts are recalculated
  from submitted orders.
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
	variation_amount,
	variation_approval_problem,
)
from sidra_realestate.services.construction_jobs import (
	approved_variation_amounts,
	check_job_access,
	check_own_private_file,
	lock_job,
	refresh_contract_values,
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
		self.amount = flt(rule(variation_amount, self.amount), 2)
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

	def check_approver(self):
		problem = variation_approval_problem(self.amount, frappe.session.user, frappe.get_roles(), self.owner)
		if problem:
			frappe.throw(_(problem), frappe.PermissionError, title=_("Approval not allowed"))

	def before_submit(self):
		self.check_approver()
		if not (self.client_approved_by or "").strip() or not self.client_approved_on:
			frappe.throw(_("Record who approved the variation for the client and when"))
		if not self.client_approval_document:
			frappe.throw(_("Attach the client's signed approval"))
		check_own_private_file(self, "client_approval_document", _("signed client approval"))

		job = lock_job(self.job)
		if not frappe.db.get_value("Sidra Construction Job", self.job, "contract_quotation"):
			frappe.throw(
				_("Job {0} has no approved contract; approve its quotation as the contract first (CON-03)").format(
					self.job
				)
			)
		if job.status not in VARIATION_STATUSES:
			frappe.throw(
				_("Job {0} is {1}; variations are approved only on a contracted job ({2})").format(
					job.name, job.status, ", ".join(VARIATION_STATUSES)
				)
			)
		approved = approved_variation_amounts(self.job, exclude=self.name)
		self.contract_value_before = flt(rule(contract_value_after, job.contract_value, approved), 2)
		self.contract_value_after = flt(
			rule(contract_value_after, job.contract_value, approved, self.amount), 2
		)
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()

	def on_submit(self):
		refresh_contract_values(self.job)

	def before_cancel(self):
		self.check_approver()
		lock_job(self.job)

	def on_cancel(self):
		refresh_contract_values(self.job)
