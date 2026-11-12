# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Construction Quotation (CON-02, CON-03; SRS v2.0 §3.1; decision G11; docs/CONSTRUCTION-CONTROLS_v0.2.md).

- Priced from the job's current BOQ (a frozen copy) or as a fixed fee (design / inspection).
- Issuing it (submit, Sidra Project Manager) is refused if the job's BOQ changed since the draft,
  if the job is closed or already contracted, or if it has expired. The job moves from Enquiry to Quoted.
- After issue the Project Manager records the client's acceptance: who, when, and the signed
  quotation as a private file on this record.
- `approve_contract` (Sidra General Manager only, G11) turns the accepted quotation into the job's
  contract: original contract value, start, duration, end, retention % and period. The job's stage
  Billing % must add up to exactly 100 (payment milestones). One contract per job.
- A contracted quotation cannot be cancelled. Nothing is invoiced or posted (CLAUDE.md rule 3).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, today

from sidra_realestate.services.construction import (
	billing_pct_problem,
	boq_key,
	retention_problem,
)
from sidra_realestate.services.construction_jobs import (
	JOB,
	check_job_access,
	check_own_private_file,
	lock_job,
	refuse_closed,
	set_job_fields,
)

BOQ_FIELDS = ("cost_code", "description", "uom", "qty", "rate")
ACCEPTANCE_FIELDS = ("client_accepted_by", "client_accepted_on", "client_acceptance_document")


def boq_rows(doc):
	return [{field: row.get(field) for field in BOQ_FIELDS} for row in doc.boq]


class SidraConstructionQuotation(Document):
	def before_insert(self):
		if self.pricing_basis == "BOQ" and not self.boq:
			for row in boq_rows(frappe.get_doc(JOB, self.job)):
				self.append("boq", row)

	def validate(self):
		check_job_access(self, "write")
		set_job_fields(self)
		self.status = "Draft"
		if not (self.scope or "").strip():
			frappe.throw(_("Describe the scope of work"))
		self.set_amounts()
		if cint(self.duration_days) <= 0:
			frappe.throw(_("The duration must be at least one day"))
		self.end_date = add_days(self.start_date, cint(self.duration_days) - 1)
		problem = retention_problem(self.retention_pct, self.retention_period_months)
		if problem:
			frappe.throw(_(problem))

	def set_amounts(self):
		total = 0
		for row in self.boq:
			if flt(row.qty) < 0 or flt(row.rate) < 0:
				frappe.throw(_("BOQ row {0}: quantity and rate cannot be negative").format(row.idx))
			row.amount = flt(flt(row.qty) * flt(row.rate), 2)
			total += row.amount
		self.boq_total = flt(total, 2)
		if self.pricing_basis == "BOQ":
			if not self.boq:
				frappe.throw(_("A BOQ quotation needs BOQ lines; enter the job's BOQ first"))
			self.fixed_fee = 0
			self.quoted_amount = self.boq_total
		else:
			self.set("boq", [])
			self.boq_total = 0
			self.quoted_amount = flt(self.fixed_fee, 2)
		if flt(self.quoted_amount) <= 0:
			frappe.throw(_("The quoted amount must be greater than zero"))

	def before_update_after_submit(self):
		"""Recording the client's acceptance on the issued quotation (the only fields open after issue)."""
		check_job_access(self, "write")
		before = self.get_doc_before_save()
		if self.contract_approved_on and before:
			if any(self.get(f) != before.get(f) for f in ACCEPTANCE_FIELDS):
				frappe.throw(_("The contract is approved; the client acceptance can no longer be changed"))
		if self.client_accepted_on:
			accepted = getdate(self.client_accepted_on)
			if accepted > getdate(today()):
				frappe.throw(_("The acceptance date cannot be in the future"))
			if accepted > getdate(self.valid_until):
				frappe.throw(
					_("The quotation expired on {0}; issue a new quotation").format(
						frappe.format(self.valid_until, "Date")
					)
				)

	def before_submit(self):
		job = lock_job(self.job)
		refuse_closed(job, _("issuing a quotation"))
		if frappe.db.get_value(JOB, self.job, "contract_quotation"):
			frappe.throw(_("Job {0} already has an approved contract").format(self.job))
		if getdate(self.valid_until) < getdate(today()):
			frappe.throw(_("This quotation has already expired; change Valid Until"))
		if self.pricing_basis == "BOQ":
			current = frappe.get_doc(JOB, self.job)
			if boq_key(boq_rows(self)) != boq_key(boq_rows(current)):
				frappe.throw(
					_("The job's BOQ changed after this quotation was drafted; make a new quotation"),
					title=_("BOQ has changed"),
				)
			self.boq_revision = current.boq_revision
		self.status = "Issued"

	def on_submit(self):
		if frappe.db.get_value(JOB, self.job, "status") == "Enquiry":
			frappe.db.set_value(JOB, self.job, "status", "Quoted")

	def before_cancel(self):
		if self.contract_approved_on:
			frappe.throw(_("A quotation that became the job's contract cannot be cancelled"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")


@frappe.whitelist()
def approve_contract(quotation: str):
	"""CON-03 / G11: the General Manager approves the accepted quotation as the job's contract."""
	frappe.only_for("Sidra General Manager")
	doc = frappe.get_doc("Sidra Construction Quotation", quotation)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Issue the quotation before approving it as the contract"))
	if doc.contract_approved_on:
		frappe.throw(_("Quotation {0} is already the job's contract").format(doc.name))
	if not (doc.client_accepted_by or "").strip() or not doc.client_accepted_on:
		frappe.throw(_("Record who accepted the quotation for the client and when"))
	if not doc.client_acceptance_document:
		frappe.throw(_("Attach the client's signed acceptance"))
	check_own_private_file(doc, "client_acceptance_document", _("signed client acceptance"))
	if getdate(doc.client_accepted_on) > getdate(doc.valid_until):
		frappe.throw(_("The client accepted after the quotation expired; issue a new quotation"))

	locked = lock_job(doc.job)
	refuse_closed(locked, _("approving a contract"))
	job = frappe.get_doc(JOB, doc.job)
	if job.contract_quotation:
		frappe.throw(
			_("Job {0} already has an approved contract ({1})").format(job.name, job.contract_quotation)
		)
	problem = billing_pct_problem([row.billing_pct for row in job.stages])
	if problem:
		frappe.throw(_("Payment milestones: {0}").format(_(problem)))

	approved_on = now_datetime()
	job.update(
		{
			"contract_quotation": doc.name,
			"contract_value": doc.quoted_amount,
			"contract_start_date": doc.start_date,
			"contract_duration_days": doc.duration_days,
			"contract_end_date": doc.end_date,
			"retention_pct": flt(doc.retention_pct),
			"retention_period_months": cint(doc.retention_period_months),
			"contract_approved_by": frappe.session.user,
			"contract_approved_on": approved_on,
		}
	)
	if job.status in ("Enquiry", "Quoted"):
		job.status = "Contracted"
	job.flags.contract_from_quotation = True
	job.save(ignore_permissions=True)  # the General Manager's approval is the authority
	doc.db_set(
		{
			"contract_approved_by": frappe.session.user,
			"contract_approved_on": approved_on,
			"status": "Contracted",
		}
	)
	job.add_comment(
		"Info",
		_("Contract approved by {0} from quotation {1}: {2}").format(
			frappe.session.user,
			doc.name,
			frappe.format(doc.quoted_amount, {"fieldtype": "Currency", "options": job.currency}),
		),
	)
	return {"job": job.name, "contract_value": job.contract_value}
