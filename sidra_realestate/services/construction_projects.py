# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G37: construction jobs are managed with native ERPNext Project and Task.

Mapping (docs/CONSTRUCTION-PROJECTS_v0.1.md):
- one Project per Sidra Construction Job (house or job), linked both ways: the job's `project`
  field and the Project's `sidra_construction_job` field;
- one Task per stage row of the job, carrying the row id in `sidra_job_stage`.

The job stays the record of the contract, stage milestones (Billing %) and certification (G11).
Tasks mirror it one way, job -> Task, on every save of the job: name, planned and actual dates,
progress, status, milestone % and amount, and certification. Nothing on a Task changes the job.
A Project is created only when someone with the rights presses "Create Project" on a job; no
existing job is converted automatically. Stage names are copied as recorded, none is invented.
No invoice, payment or ledger entry is created.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from sidra_realestate.services.construction import CLOSED_STATUSES
from sidra_realestate.services.construction_jobs import lock_job

JOB = "Sidra Construction Job"

TASK_STATUS = {"Planned": "Open", "In Progress": "Working", "Completed": "Completed"}

CUSTOM_FIELDS = {
	"Project": [
		{
			"fieldname": "sidra_construction_job",
			"label": "Construction Job",
			"fieldtype": "Link",
			"options": JOB,
			"insert_after": "project_name",
			"read_only": 1,
			"search_index": 1,
		},
	],
	"Task": [
		{
			"fieldname": "sidra_stage_section",
			"label": "Construction stage",
			"fieldtype": "Section Break",
			"insert_after": "description",
			"collapsible": 0,
		},
		{
			"fieldname": "sidra_construction_job",
			"label": "Construction Job",
			"fieldtype": "Link",
			"options": JOB,
			"insert_after": "sidra_stage_section",
			"read_only": 1,
			"search_index": 1,
		},
		{
			"fieldname": "sidra_job_stage",
			"label": "Job stage row",
			"fieldtype": "Data",
			"insert_after": "sidra_construction_job",
			"read_only": 1,
			"hidden": 1,
			"search_index": 1,
		},
		{
			"fieldname": "sidra_billing_pct",
			"label": "Payment milestone %",
			"fieldtype": "Percent",
			"insert_after": "sidra_job_stage",
			"read_only": 1,
			"description": "From the job's signed terms. Not an invoice.",
		},
		{
			"fieldname": "sidra_milestone_amount",
			"label": "Milestone amount",
			"fieldtype": "Currency",
			"insert_after": "sidra_billing_pct",
			"read_only": 1,
		},
		{
			"fieldname": "sidra_stage_col",
			"fieldtype": "Column Break",
			"insert_after": "sidra_milestone_amount",
		},
		{
			"fieldname": "sidra_certified",
			"label": "Stage certified",
			"fieldtype": "Check",
			"insert_after": "sidra_stage_col",
			"read_only": 1,
		},
		{
			"fieldname": "sidra_certified_by",
			"label": "Certified by",
			"fieldtype": "Link",
			"options": "User",
			"insert_after": "sidra_certified",
			"read_only": 1,
		},
		{
			"fieldname": "sidra_certified_on",
			"label": "Certified on",
			"fieldtype": "Datetime",
			"insert_after": "sidra_certified_by",
			"read_only": 1,
		},
	],
}


def ensure_project_fields():
	"""Add the link fields on Project and Task (after_install / after_migrate). Idempotent."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


@frappe.whitelist(methods=["POST"])
def create_project(job: str):
	"""Create the Project and one Task per stage for `job`, and link them. Returns the Project."""
	locked = lock_job(job)
	doc = frappe.get_doc(JOB, job)
	doc.check_permission("write")
	if not frappe.has_permission("Project", "create") or not frappe.has_permission("Task", "create"):
		frappe.throw(_("You are not permitted to create Projects and Tasks"), frappe.PermissionError)
	if locked.status in CLOSED_STATUSES:
		frappe.throw(_("Job {0} is {1}; no Project can be created").format(job, locked.status))
	if doc.project:
		frappe.throw(_("Job {0} is already linked to Project {1}").format(job, doc.project))
	if not doc.stages:
		frappe.throw(_("Job {0} has no stages to plan").format(job))

	start, end = date_span(doc)
	place = doc.plot_number or doc.site_location or doc.customer
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": f"{doc.name} · {place}"[:140],
			"company": doc.company,
			"customer": doc.customer,
			"expected_start_date": start,
			"expected_end_date": end,
			# G30: the simple average of recorded stage completion.
			"percent_complete_method": "Task Progress",
			"sidra_construction_job": doc.name,
		}
	).insert()
	for row in doc.stages:
		frappe.get_doc({"doctype": "Task", **task_values(doc, row, project.name)}).insert()

	doc.project = project.name
	doc.save()
	doc.add_comment("Info", _("ERPNext Project {0} created with one Task per stage").format(project.name))
	return {"project": project.name}


def sync_tasks(doc):
	"""Mirror the job's stages onto its Project's Tasks (called from the job's on_update)."""
	if not doc.project or not frappe.get_meta("Project").has_field("sidra_construction_job"):
		return
	if not frappe.db.exists("Project", doc.project):
		return
	if frappe.db.get_value("Project", doc.project, "sidra_construction_job") != doc.name:
		return  # a Project linked by hand, not one this app created: left alone
	widen_project(doc)
	tasks = {
		t.sidra_job_stage: t.name
		for t in frappe.get_all(
			"Task",
			filters={"project": doc.project, "sidra_construction_job": doc.name},
			fields=["name", "sidra_job_stage"],
		)
	}
	rows = {row.name for row in doc.stages}
	for row in doc.stages:
		values = task_values(doc, row, doc.project)
		if row.name in tasks:
			task = frappe.get_doc("Task", tasks[row.name])
			if task.status == "Completed" and values["status"] != "Completed":
				task.completed_on = None
			task.update(values)
		else:
			task = frappe.get_doc({"doctype": "Task", **values})
		# The job's own permission was checked when it was saved; the Task is its mirror.
		task.save(ignore_permissions=True)
	for stage, name in tasks.items():
		if stage not in rows:
			task = frappe.get_doc("Task", name)
			if task.status != "Cancelled":
				task.status = "Cancelled"
				task.save(ignore_permissions=True)


def task_values(doc, row, project):
	status = TASK_STATUS.get(row.status or "Planned", "Open")
	values = {
		"subject": f"{row.idx}. {row.stage_name}"[:140],
		"project": project,
		"company": doc.company,
		"exp_start_date": row.planned_start,
		"exp_end_date": row.planned_end,
		"act_start_date": row.actual_start,
		"act_end_date": row.actual_end,
		"progress": flt(row.completion_pct),
		"status": status,
		"sidra_construction_job": doc.name,
		"sidra_job_stage": row.name,
		"sidra_billing_pct": flt(row.billing_pct),
		"sidra_milestone_amount": flt(row.billing_amount),
		"sidra_certified": row.certified or 0,
		"sidra_certified_by": row.certified_by,
		"sidra_certified_on": row.certified_on,
	}
	if status == "Completed":
		done = getdate(row.actual_end) if row.actual_end else getdate(today())
		values["completed_on"] = min(done, getdate(today()))
	return values


def date_span(doc):
	"""The earliest and latest date of the contract and the stages' planned and actual dates."""
	dates = [
		getdate(d)
		for d in [doc.contract_start_date, doc.contract_end_date]
		+ [
			row.get(f)
			for row in doc.stages
			for f in ("planned_start", "planned_end", "actual_start", "actual_end")
		]
		if d
	]
	return (min(dates), max(dates)) if dates else (None, None)


def widen_project(doc):
	"""ERPNext refuses Task dates outside the Project's expected dates, so the Project grows to fit."""
	start, end = date_span(doc)
	if not start:
		return
	current = frappe.db.get_value(
		"Project", doc.project, ["expected_start_date", "expected_end_date"], as_dict=True
	)
	new_start = min(start, getdate(current.expected_start_date)) if current.expected_start_date else start
	new_end = max(end, getdate(current.expected_end_date)) if current.expected_end_date else end
	if new_start != current.expected_start_date or new_end != current.expected_end_date:
		frappe.db.set_value(
			"Project", doc.project, {"expected_start_date": new_start, "expected_end_date": new_end}
		)
