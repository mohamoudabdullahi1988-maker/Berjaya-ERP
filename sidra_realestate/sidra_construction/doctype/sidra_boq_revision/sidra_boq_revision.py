# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra BOQ Revision (CON-02 revisions; SRS v2.0 §3.1, §4.1; docs/CONSTRUCTION-CONTROLS_v0.2.md).

- A draft starts from the job's current BOQ and records which approved revision it was based on.
- Approval (submit, Sidra Project Manager) is refused if another revision was approved meanwhile,
  or if the draft changes nothing. It numbers the revision and copies the lines to the job.
- From the first approved revision on, the job's BOQ changes only through a new revision.
- An approved revision is never cancelled: approve a new revision instead, so history is kept.
- Planning only: no quotation, invoice or posting.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from sidra_realestate.services.construction import boq_key
from sidra_realestate.services.construction_jobs import (
	JOB,
	check_job_access,
	lock_job,
	refuse_closed,
	set_job_fields,
)

BOQ_FIELDS = ("cost_code", "description", "uom", "qty", "rate")


def boq_rows(doc):
	return [{field: row.get(field) for field in BOQ_FIELDS} for row in doc.boq]


class SidraBOQRevision(Document):
	def before_insert(self):
		job = frappe.get_doc(JOB, self.job)
		self.base_revision = job.boq_revision
		if not self.boq:
			for row in boq_rows(job):
				self.append("boq", row)

	def validate(self):
		# Approvers (submit) need only read access to the job; drafts need write.
		check_job_access(self, "write" if self.docstatus == 0 else "read")
		set_job_fields(self)
		if not (self.reason or "").strip():
			frappe.throw(_("Give a reason for the revision"))
		if not self.boq:
			frappe.throw(_("A BOQ revision needs at least one line"))
		total = 0
		for row in self.boq:
			if flt(row.qty) < 0 or flt(row.rate) < 0:
				frappe.throw(_("BOQ row {0}: quantity and rate cannot be negative").format(row.idx))
			row.amount = flt(flt(row.qty) * flt(row.rate), 2)
			total += row.amount
		self.boq_total = flt(total, 2)

	def before_submit(self):
		job = lock_job(self.job)
		refuse_closed(job, _("a BOQ revision"))
		if (job.boq_revision or None) != (self.base_revision or None):
			frappe.throw(
				_(
					"Revision {0} of this job's BOQ was approved after this draft was made. "
					"Make a new revision from the current BOQ."
				).format(job.boq_revision),
				title=_("BOQ has changed"),
			)
		if boq_key(boq_rows(self)) == boq_key(boq_rows(frappe.get_doc(JOB, self.job))):
			frappe.throw(_("This revision makes no change to the job's BOQ"))
		self.revision_no = (job.boq_revision_no or 0) + 1
		self.previous_total = flt(job.boq_total, 2)
		self.difference = flt(self.boq_total - self.previous_total, 2)
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()

	def on_submit(self):
		job = frappe.get_doc(JOB, self.job)
		job.set("boq", [])
		for row in boq_rows(self):
			job.append("boq", row)
		job.boq_revision = self.name
		job.boq_revision_no = self.revision_no
		job.flags.boq_from_revision = True
		job.save(ignore_permissions=True)  # the approval itself is the authority
		job.add_comment(
			"Info",
			_("BOQ revision {0} (No. {1}) approved by {2}: total {3} → {4}").format(
				self.name, self.revision_no, self.approved_by, self.previous_total, self.boq_total
			),
		)

	def before_cancel(self):
		frappe.throw(
			_("An approved BOQ revision cannot be cancelled; approve a new revision instead"),
			title=_("Not allowed"),
		)
