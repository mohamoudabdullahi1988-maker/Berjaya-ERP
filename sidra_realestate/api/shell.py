# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The Sidra front page at /sidra (docs/SHELL_v0.1.md): four doors and two workflows.

Read-only. Every count comes from `frappe.get_list`, so Company and record User Permissions
apply; a step the user cannot read is left out, never shown as zero. Nothing is whitelisted:
the page is rendered on the server and adds no HTTP API.
"""

import json
from urllib.parse import quote, urlencode

import frappe
from frappe import _

STAFF_DASHBOARD = "/sidra-staff/"
DESK = "/desk"

# (label, doctype, filters, hint). `attention` steps are work waiting on someone.
SALES_STEPS = (
	("Open leads", "Lead", {"status": ("not in", ["Converted", "Do Not Contact"])}, "Enquiries not yet won"),
	("Quotations issued", "Sidra Sale Quotation", {"status": "Issued"}, "With the buyer, not expired"),
	("Active reservations", "Sidra Reservation", {"status": "Active"}, "Plots held for a buyer"),
	("Contracts in draft", "Sidra Sale Contract", {"docstatus": 0}, "Waiting for confirmation"),
	("Confirmed contracts", "Sidra Sale Contract", {"docstatus": 1}, "Signed and in force"),
	(
		"Title transfers open",
		"Sidra Title Transfer",
		{"status": ("in", ["In Progress", "Due Soon", "Overdue"])},
		"Deeds still to hand over",
	),
)
SALES_ATTENTION = (
	("Buyer KYC to verify", "Sidra Customer KYC", {"status": "Draft"}),
	("Title transfers overdue", "Sidra Title Transfer", {"status": "Overdue"}),
)
SALES_NEW = (
	("New quotation", "Sidra Sale Quotation"),
	("New reservation", "Sidra Reservation"),
	("New contract", "Sidra Sale Contract"),
)
SALES_BROWSE = (("Plots and units", "Sidra Unit"), ("Schemes", "Sidra Scheme"), ("Customers", "Customer"))

CONSTRUCTION_STEPS = (
	("Enquiries", "Sidra Construction Job", {"status": "Enquiry"}, "Jobs not yet quoted"),
	("Quoted", "Sidra Construction Job", {"status": "Quoted"}, "Quotation with the client"),
	("Contracted", "Sidra Construction Job", {"status": "Contracted"}, "Approved, not yet started"),
	(
		"In progress",
		"Sidra Construction Job",
		{"status": ("in", ["In Progress", "On Hold"])},
		"On site, including on hold",
	),
	(
		"Completed",
		"Sidra Construction Job",
		{"status": ("in", ["Completed", "Defects Period"])},
		"Finished or in the defects period",
	),
)
CONSTRUCTION_ATTENTION = (
	("Quotations in draft", "Sidra Construction Quotation", {"docstatus": 0}),
	("BOQ revisions to approve", "Sidra BOQ Revision", {"docstatus": 0}),
	("Variation orders to approve", "Sidra Variation Order", {"docstatus": 0}),
	("Inspection reports to approve", "Sidra Inspection Report", {"docstatus": 0}),
)
CONSTRUCTION_NEW = (
	("New job", "Sidra Construction Job"),
	("New inspection report", "Sidra Inspection Report"),
)
CONSTRUCTION_BROWSE = (("All jobs", "Sidra Construction Job"), ("Customers", "Customer"))

FINANCIAL_REPORTS = (
	"General Ledger",
	"Trial Balance",
	"Profit and Loss Statement",
	"Balance Sheet",
	"Accounts Receivable",
	"Accounts Payable",
)


def is_staff() -> bool:
	roles = set(frappe.get_roles())
	return "System Manager" in roles or any(role.startswith("Sidra ") for role in roles)


def _slug(doctype) -> str:
	return doctype.lower().replace(" ", "-")


def _list_url(doctype, filters=None) -> str:
	query = {}
	for field, value in (filters or {}).items():
		query[field] = json.dumps(list(value)) if isinstance(value, tuple) else value
	return f"{DESK}/{_slug(doctype)}" + ("?" + urlencode(query) if query else "")


def _can(doctype, ptype="read") -> bool:
	return bool(frappe.db.exists("DocType", doctype)) and bool(frappe.has_permission(doctype, ptype))


def _count(doctype, filters):
	"""Permission-filtered count, or None when the user may not read the record type."""
	if not _can(doctype):
		return None
	try:
		return len(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=0))
	except frappe.PermissionError:
		return None


def _steps(rows):
	steps = []
	for label, doctype, filters, *hint in rows:
		count = _count(doctype, filters)
		if count is None:
			continue
		steps.append(
			{
				"label": _(label),
				"count": count,
				"hint": _(hint[0]) if hint else "",
				"href": _list_url(doctype, filters),
			}
		)
	return steps


def _links(rows, ptype):
	return [
		{"label": _(label), "href": f"{DESK}/{_slug(doctype)}" + ("/new" if ptype == "create" else "")}
		for label, doctype in rows
		if _can(doctype, ptype)
	]


def _service(key, title, summary, steps, attention, new, browse):
	steps = _steps(steps)
	if not steps:
		return None
	return {
		"key": key,
		"title": _(title),
		"summary": _(summary),
		"steps": steps,
		"attention": [row for row in _steps(attention) if row["count"]],
		"new": _links(new, "create"),
		"browse": _links(browse, "read"),
	}


def build_shell() -> dict:
	"""What the signed-in user's front page shows. Call only for Sidra staff."""
	services = [
		service
		for service in (
			_service(
				"real-estate",
				"Real Estate Sales",
				"From first enquiry to the title deed.",
				SALES_STEPS,
				SALES_ATTENTION,
				SALES_NEW,
				SALES_BROWSE,
			),
			_service(
				"construction",
				"Construction",
				"From enquiry to a finished, certified job.",
				CONSTRUCTION_STEPS,
				CONSTRUCTION_ATTENTION,
				CONSTRUCTION_NEW,
				CONSTRUCTION_BROWSE,
			),
		)
		if service
	]
	reports = (
		[
			{"label": _(name), "href": f"{DESK}/query-report/{quote(name)}"}
			for name in FINANCIAL_REPORTS
			if frappe.db.exists("Report", name)
		]
		if _can("GL Entry")
		else []
	)
	doors = [
		{
			"key": "dashboard",
			"title": _("Executive Dashboard"),
			"summary": _("Sales, collections, plots and jobs at a glance."),
			"href": STAFF_DASHBOARD,
		}
	]
	if reports:
		doors.append(
			{
				"key": "financials",
				"title": _("Financials"),
				"summary": _("Ledger, statements, receivables and payables."),
				"href": "#financials",
			}
		)
	for service in services:
		doors.append(
			{
				"key": service["key"],
				"title": service["title"],
				"summary": service["summary"],
				"href": "#" + service["key"],
				"waiting": sum(row["count"] for row in service["attention"]),
			}
		)
	return {
		"full_name": frappe.utils.get_fullname(frappe.session.user),
		"doors": doors,
		"services": services,
		"reports": reports,
		"all_records": DESK + "/sidra-sale-contract" if _can("Sidra Sale Contract") else DESK,
	}
