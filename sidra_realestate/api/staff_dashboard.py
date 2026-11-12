"""Staff dashboard snapshot (clients/staff/docs/API-CONTRACT.md, "Dashboard"; schema_version 1).

Every query goes through `frappe.get_list`, so the user's role permissions and Company User
Permissions are the security boundary. One Company and its currency per response.

Groups without real data are returned as unavailable with a reason, never as zero:
- payments: receipts are not recorded in ERPNext yet (D8; Finance gate). Scheduled amounts are
  obligations, not receipts or arrears;
- sales pipeline: lead qualification stages are not defined yet.
Agreed contract value is commercial value, not revenue.

Groups whose record types the user's role cannot read are returned as null/empty, never as an
error for the whole page, so construction-only roles still get their view. Money is summed as
exact decimals; a missing or invalid amount makes its total unknown (null), never zero.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import get_system_timezone, getdate

from sidra_realestate.api.executive_dashboard import ACTIVE_JOBS  # same scope as stage exceptions
from sidra_realestate.api.location_geometry import extract_point, legacy_point
from sidra_realestate.services.executive_metrics import (
	decimal_amount,
	period_window,
	site_period_bounds,
	stage_overdue,
)
from sidra_realestate.services.executive_metrics import money as exact_money

PERIODS = {"this_month", "last_30_days", "last_90_days"}
LOCATION_DOCTYPES = ("Sidra Unit", "Sidra Construction Job")
LIST_LIMIT = 20
LOCATION_LIMIT = 500


NO_CONTRACT_ACCESS = "Your role does not include sale contracts."


def money(value) -> str | None:
	"""Exact two-place decimal string; None when no amount is recorded."""
	if value is None or str(value).strip() == "":
		return None
	return exact_money(value)


def total(values) -> str | None:
	"""Exact decimal sum; None when any amount is missing or invalid (unknown is never zero)."""
	result = Decimal(0)
	for value in values:
		try:
			result += decimal_amount(value)
		except ValueError:
			return None
	return exact_money(result)


def _can_read(doctype) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _period_start(period):
	from sidra_realestate.api.executive_dashboard import snapshot_time

	return period_window(period, snapshot_time().date())[0]


def _companies():
	try:
		rows = frappe.get_list(
			"Company",
			fields=["name", "company_name", "default_currency"],
			order_by="name",
			limit_page_length=0,
		)
	except frappe.PermissionError:
		rows = []
	if not rows or any(not row.default_currency for row in rows):
		# v16 Company Select permission can return names with other fields redacted, not
		# necessarily a PermissionError. Retain readable metadata; hydrate only Companies
		# established by readable operational parents; a construction-only Company need
		# not have property inventory. Never hydrate arbitrary Company Select results.
		known = {row.name: row for row in rows if row.default_currency}
		names = set()
		for doctype in ("Sidra Unit", "Sidra Construction Job", "Sidra Sale Contract", "Sidra Reservation"):
			if frappe.has_permission(doctype, "read"):
				names.update(
					r.company
					for r in frappe.get_list(doctype, fields=["company"], limit_page_length=0)
					if r.company
				)
		for name in sorted(names):
			known.setdefault(
				name,
				frappe._dict(
					name=name,
					company_name=name,
					default_currency=frappe.get_cached_value("Company", name, "default_currency"),
				),
			)
		rows = [known[name] for name in sorted(known)]
	for row in rows:
		row.company_name = row.company_name or row.name
	return rows


def _role_label():
	roles = set(frappe.get_roles())
	for role in (
		"Sidra General Manager",
		"Sidra Sales Manager",
		"Sidra Finance Reviewer",
		"Sidra Project Manager",
		"Sidra Sales User",
		"Sidra Inspector",
	):
		if role in roles:
			return role.removeprefix("Sidra ")
	return "System Manager" if "System Manager" in roles else "Staff"


def _staff_only():
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in first"), frappe.AuthenticationError)
	roles = set(frappe.get_roles())
	if "System Manager" not in roles and not any(r.startswith("Sidra ") for r in roles):
		frappe.throw(_("The staff dashboard is for Sidra staff"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def get_dashboard(company: str | None = None, period: str = "this_month", project: str | None = None) -> dict:
	from sidra_realestate.api.executive_dashboard import executive_snapshot, snapshot_time

	_staff_only()
	if project:
		frappe.throw(_("Project associations are not configured; choose all permitted projects"))
	if period not in PERIODS:
		frappe.throw(_("Period must be one of {0}").format(", ".join(sorted(PERIODS))))
	companies = _companies()
	if not companies:
		frappe.throw(_("No Company is available to you"), frappe.PermissionError)
	permitted = {c.name: c for c in companies}
	if company and company not in permitted:
		frappe.throw(_("Company {0} is not available to you").format(company), frappe.PermissionError)
	scope = permitted[company] if company else companies[0]
	if not scope.default_currency:
		frappe.throw(_("Company currency metadata is unavailable; no monetary totals can be established"))
	now = snapshot_time()
	today = now.date()
	start, _end = period_window(period, today)

	payload = {
		"schema_version": 1,
		"as_of": now.isoformat(timespec="seconds"),
		"scope": {
			"company_id": scope.name,
			"company_name": scope.company_name,
			"project_id": None,
			"role_label": _role_label(),
		},
		"projects": [],
		"companies": [{"id": c.name, "name": c.company_name} for c in companies],
		"currency": scope.default_currency,
		"period": period,
	}
	payload.update(_property_and_summary(scope.name, start, today, scope.default_currency))
	payload["schedule"] = _schedule(scope.name, today, scope.default_currency)
	payload["contracts"] = _contracts(scope.name)
	payload["locations"] = _locations(scope.name)
	payload["sales"] = {
		"available": False,
		"reason": "Lead qualification stages are not defined yet, so no pipeline or conversion is shown.",
	}
	payload["payments"] = {
		"available": False,
		"reason": "Payments are not recorded in ERPNext yet (Finance gate). Scheduled amounts are not receipts or arrears.",
	}
	payload["jobs"] = _jobs(scope.name, today)
	payload["executive"] = executive_snapshot(scope.name, scope.default_currency, period, now)
	if payload["executive"].get("finance_demo") is not None:
		payload["payments"] = payload["executive"].pop("finance_demo")
	return payload


def _property_and_summary(company, start, today, currency):
	units = (
		frappe.get_list("Sidra Unit", filters={"company": company}, fields=["status"], limit_page_length=0)
		if _can_read("Sidra Unit")
		else None
	)
	counts = {}
	for u in units or []:
		counts[u.status] = counts.get(u.status, 0) + 1
	confirmed = (
		frappe.get_list(
			"Sidra Sale Contract",
			filters={
				"company": company,
				"currency": currency,
				"docstatus": 1,
				"signed_on": ["between", [start, today]],
			},
			fields=["agreed_price"],
			limit_page_length=0,
		)
		if _can_read("Sidra Sale Contract")
		else None
	)
	try:
		creation_start, creation_end = site_period_bounds(start, today, get_system_timezone())
		new_leads = len(
			frappe.get_list(
				"Lead",
				filters={
					"creation": ["between", [creation_start, creation_end]],
					"company": company,
				},
				pluck="name",
				limit_page_length=0,
			)
		)
	except frappe.PermissionError:
		new_leads = None
	return {
		"summary": {
			"new_leads": new_leads,
			"units_available": None if units is None else counts.get("Available", 0),
			"active_reservations": len(
				frappe.get_list(
					"Sidra Reservation",
					filters={"company": company, "status": "Active"},
					pluck="name",
					limit_page_length=0,
				)
			)
			if _can_read("Sidra Reservation")
			else None,
			"confirmed_contracts": None if confirmed is None else len(confirmed),
			"agreed_contract_value": None
			if confirmed is None
			else total(c.agreed_price for c in confirmed),
		},
		"property": {
			"total": None if units is None else len(units),
			"counts": [{"status": s, "count": n} for s, n in sorted(counts.items())],
		},
	}


def _schedule(company, today, currency):
	"""Scheduled amounts of confirmed contracts from today on. Obligations, not receipts.

	"Next 30 days" is tomorrow through day 30, the same window as the executive
	`due_next_30_days`; rows due today have their own bucket so none are dropped.
	"""
	if not _can_read("Sidra Sale Contract"):
		return {"available": False, "reason": NO_CONTRACT_ACCESS, "buckets": [], "upcoming": []}
	contracts = {
		c.name: c
		for c in frappe.get_list(
			"Sidra Sale Contract",
			filters={"company": company, "currency": currency, "docstatus": 1, "signed_on": ["<=", today]},
			fields=["name", "external_reference", "customer", "currency"],
			limit_page_length=0,
		)
	}
	if not contracts:
		return {"available": True, "buckets": [], "upcoming": []}
	rows = frappe.get_all(  # child rows of contracts the user may read (checked above)
		"Sidra Installment Line",
		filters={
			"parenttype": "Sidra Sale Contract",
			"parent": ["in", list(contracts)],
			"due_date": [">=", today],
		},
		fields=["parent", "due_date", "amount", "row_type"],
		order_by="due_date asc",
		limit_page_length=0,
	)
	edges = ((_("Due today"), 0), (_("Next 30 days"), 30), (_("31-60 days"), 60), (_("61-90 days"), 90))
	amounts = [[] for _edge in edges]
	for r in rows:
		days = (getdate(r.due_date) - today).days
		for i, (_label, limit) in enumerate(edges):
			if days <= limit:
				amounts[i].append(r.amount)
				break
	upcoming = [
		{
			"contract_id": r.parent,
			"external_reference": contracts[r.parent].external_reference,
			"customer_display": contracts[r.parent].customer,
			"due_date": str(r.due_date),
			"amount": money(r.amount),
			"currency": contracts[r.parent].currency,
			"row_type": r.row_type or "Installment",
		}
		for r in rows[:LIST_LIMIT]
	]
	return {
		"available": True,
		"buckets": [
			{"label": label, "amount": total(a)} for (label, _l), a in zip(edges, amounts, strict=True)
		],
		"upcoming": upcoming,
	}


def _contracts(company):
	if not _can_read("Sidra Sale Contract"):
		return []
	rows = frappe.get_list(
		"Sidra Sale Contract",
		filters={"company": company, "docstatus": ["<", 2]},
		fields=[
			"name",
			"external_reference",
			"customer",
			"docstatus",
			"agreed_price",
			"currency",
			"signed_on",
		],
		order_by="modified desc",
		limit_page_length=LIST_LIMIT,
	)
	units = {}
	if rows:
		for u in frappe.get_all(
			"Sidra Contract Unit",
			filters={"parenttype": "Sidra Sale Contract", "parent": ["in", [r.name for r in rows]]},
			fields=["parent", "unit"],
			order_by="idx asc",
		):
			units.setdefault(u.parent, []).append(u.unit)
	return [
		{
			"id": r.name,
			"reference": r.external_reference or r.name,
			"customer_display": r.customer,
			"unit_label": ", ".join(units.get(r.name, [])),
			"status": "Confirmed" if r.docstatus == 1 else "Draft",
			"value": money(r.agreed_price),
			"currency": r.currency,
			"signed_on": str(r.signed_on) if r.signed_on else None,
		}
		for r in rows
	]


def _locations(company):
	out = []
	for doctype, label_field, area_field in (
		("Sidra Unit", "unit_code", "scheme"),
		("Sidra Construction Job", "customer", "site_location"),
	):
		if not frappe.has_permission(doctype, "read"):
			continue  # roles without access to this record type see none of its pins
		fields = ["name", label_field, area_field, "status", "modified", "sidra_location"]
		if doctype == "Sidra Construction Job":
			fields.append("gps")
		can_write = frappe.has_permission(doctype, "write")
		for r in frappe.get_list(
			doctype, filters={"company": company}, fields=fields, limit_page_length=LOCATION_LIMIT
		):
			point = extract_point(r.sidra_location) or (
				legacy_point(r.get("gps")) if not r.sidra_location else None
			)
			out.append(
				{
					"doctype": doctype,
					"name": r.name,
					"label": r.get(label_field) or r.name,
					"area": r.get(area_field),
					"status": r.status,
					"latitude": point[0] if point else None,
					"longitude": point[1] if point else None,
					"modified": str(r.modified),
					"can_write": bool(can_write and frappe.has_permission(doctype, "write", r.name)),
				}
			)
	return out


def _jobs(company, today):
	if not frappe.has_permission("Sidra Construction Job", "read"):
		return {"available": False, "reason": "Your role does not include construction jobs."}
	jobs = frappe.get_list(
		"Sidra Construction Job",
		filters={"company": company},
		fields=["name", "customer", "status"],
		order_by="modified desc",
		limit_page_length=0,
	)
	if not jobs:
		return {"available": False, "reason": "There are no construction jobs for this Company yet."}
	stages = frappe.get_all(
		"Sidra Project Stage",
		filters={"parenttype": "Sidra Construction Job", "parent": ["in", [j.name for j in jobs]]},
		fields=["parent", "stage_name", "status", "planned_end", "actual_end", "completion_pct", "idx"],
		order_by="idx asc",
	)
	active = {j.name for j in jobs if j.status in ACTIVE_JOBS}
	by_job = {}
	for s in stages:
		by_job.setdefault(s.parent, []).append(s)
	try:
		overdue = sum(1 for s in stages if s.parent in active and stage_overdue(s, today))
	except ValueError:
		overdue = None  # an invalid recorded completion makes the count unknown, not zero
	items = []
	for j in jobs[:LIST_LIMIT]:
		own = by_job.get(j.name, [])
		nxt = next((s for s in own if s.status != "Completed"), None)
		items.append(
			{
				"id": j.name,
				"label": j.customer or j.name,
				"status": j.status,
				# recorded stage completion only; no estimate is invented
				"progress": round(sum(float(s.completion_pct or 0) for s in own) / len(own)) if own else None,
				"next_milestone": nxt.stage_name if nxt else None,
				"due_date": str(nxt.planned_end) if nxt and nxt.planned_end else None,
			}
		)
	return {
		"available": True,
		"active": sum(1 for j in jobs if j.status in ("Contracted", "In Progress")),
		"overdue_milestones": overdue,
		"awaiting_inspection": None,  # no inspection records exist yet
		"completed": sum(1 for j in jobs if j.status == "Completed"),
		"items": items,
	}
