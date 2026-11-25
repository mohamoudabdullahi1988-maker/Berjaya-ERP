# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Frappe-side helpers for construction records linked to a Sidra Construction Job.

See docs/CONSTRUCTION-CONTROLS_v0.2.md. Nothing here creates an invoice or posts to the ledger.
"""

import frappe
from frappe import _

from sidra_realestate.services.construction import CLOSED_STATUSES, money
from sidra_realestate.services.files import check_own_private_file  # noqa: F401 (re-exported)

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


def approved_variation_amounts(job, exclude=None):
	filters = {"job": job, "docstatus": 1}
	if exclude:
		filters["name"] = ("!=", exclude)
	return [money(a) for a in frappe.get_all("Sidra Variation Order", filters=filters, pluck="amount")]


def refresh_contract_values(job):
	"""Recalculate the job's approved variations, current value and milestone amounts (job validate)."""
	doc = frappe.get_doc(JOB, job)
	doc.save(ignore_permissions=True)  # the approval that called this is the authority
