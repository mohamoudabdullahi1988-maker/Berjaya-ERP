# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Frappe-side helpers for construction records linked to a Sidra Construction Job.

See docs/CONSTRUCTION-CONTROLS_v0.2.md. Nothing here creates an invoice or posts to the ledger.
"""

import frappe
from frappe import _

from sidra_realestate.services.construction import CLOSED_STATUSES, money

JOB = "Sidra Construction Job"


def check_job_access(doc, ptype="read"):
	"""The linked job decides access: Company is fetched from it after Frappe's own create check."""
	if doc.flags.ignore_permissions:
		return
	frappe.get_doc(JOB, doc.job).check_permission(ptype)


def set_job_fields(doc):
	"""Company, customer and currency always follow the job (never trusted from the client)."""
	job = frappe.db.get_value(JOB, doc.job, ["company", "customer", "status"], as_dict=True)
	if not job:
		frappe.throw(_("Unknown construction job {0}").format(doc.job), frappe.DoesNotExistError)
	doc.company = job.company
	doc.customer = job.customer
	doc.currency = frappe.get_cached_value("Company", job.company, "default_currency")
	return job


def lock_job(name):
	"""Row lock on the job, so approvals on the same job are serialised."""
	job = frappe.db.get_value(
		JOB,
		name,
		["name", "status", "contract_value", "boq_revision", "boq_revision_no", "boq_total"],
		as_dict=True,
		for_update=True,
	)
	if not job:
		frappe.throw(_("Unknown construction job {0}").format(name), frappe.DoesNotExistError)
	return job


def refuse_closed(job, action):
	if job.status in CLOSED_STATUSES:
		frappe.throw(_("Job {0} is {1}; {2} is not allowed").format(job.name, job.status, action))


def check_own_private_file(doc, fieldname, label):
	"""The file in `fieldname` must be uploaded to this record's own field, private, and used nowhere else.

	Same rule as the sale contract's signed copy (review finding 1 on develop @ cbce4f3).
	"""
	file_url = doc.get(fieldname)
	files = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=["name", "attached_to_doctype", "attached_to_name", "attached_to_field"],
	)
	own = [
		f
		for f in files
		if (f.attached_to_doctype, f.attached_to_name, f.attached_to_field)
		== (doc.doctype, doc.name, fieldname)
	]
	if not own:
		frappe.throw(_("Upload the {0} to this record's own field and save before submitting").format(label))
	if len(own) != len(files):
		frappe.throw(
			_("This {0} file is also used by another record; upload this record's own copy").format(label),
			frappe.PermissionError,
		)
	file_doc = frappe.get_doc("File", own[0].name)
	if not file_doc.is_private:
		frappe.throw(_("The {0} must be a private file").format(label))
	if not file_doc.has_permission("read"):
		frappe.throw(_("You cannot read this {0}").format(label), frappe.PermissionError)
	if not file_doc.exists_on_disk():
		frappe.throw(_("The {0} file is missing from the server; upload it again").format(label))


def approved_variation_amounts(job, exclude=None):
	filters = {"job": job, "docstatus": 1}
	if exclude:
		filters["name"] = ("!=", exclude)
	return [money(a) for a in frappe.get_all("Sidra Variation Order", filters=filters, pluck="amount")]


def refresh_contract_values(job):
	"""Recalculate the job's approved variations, current value and milestone amounts (job validate)."""
	doc = frappe.get_doc(JOB, job)
	doc.save(ignore_permissions=True)  # the approval that called this is the authority
