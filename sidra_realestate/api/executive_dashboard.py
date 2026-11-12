"""Permission-filtered executive snapshot and native report evidence; no writebacks."""

from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import get_system_timezone, getdate

from sidra_realestate.services.executive_metrics import (
	decimal_amount,
	money,
	month_starts,
	period_window,
	registration_day,
	stage_date_exception,
)

REPORT = "Sidra Executive Detail"
MANAGEMENT_ROLES = {"Sidra General Manager", "System Manager"}
ACTIVE_JOBS = {"Contracted", "In Progress", "On Hold"}
EVIDENCE = {
	"sales_value",
	"available_units",
	"scheduled_dues",
	"stage_exceptions",
	"reservations_due",
	"inventory_age",
	"cancelled_contracts",
}
FINANCE_REASON = _(
	"Receipt and allocation integration is not approved/available. Schedule rows are not cash or unpaid balances."
)


def snapshot_time():
	return datetime.now(ZoneInfo("Africa/Mogadishu"))


def management_access():
	return bool(MANAGEMENT_ROLES.intersection(frappe.get_roles()))


def unavailable(reason):
	return {"available": False, "reason": reason}


def _read(doctype, company, fields, **filters):
	if not frappe.has_permission(doctype, "read"):
		return None
	return frappe.get_list(
		doctype,
		filters={"company": company, **filters},
		fields=fields,
		order_by="name asc",
		limit_page_length=0,
	)


def _children(doctype, parents, parenttype, parentfield, fields, **filters):
	# Only child rows of permission-filtered, consistent parents; never an unrestricted parent query.
	if not parents:
		return []
	return frappe.get_all(
		doctype,
		filters={
			"parent": ["in", list(parents)],
			"parenttype": parenttype,
			"parentfield": parentfield,
			**filters,
		},
		fields=["name", "parent", *fields],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)


class Sources:
	def __init__(self, company, currency, today):
		self.company, self.currency, self.today = company, currency, today
		self.site_timezone = get_system_timezone()
		schemes = _read("Sidra Scheme", company, ["name"])
		units = _read(
			"Sidra Unit", company, ["name", "unit_code", "scheme", "status", "cash_price", "creation"]
		)
		self.units = (
			None
			if schemes is None or units is None
			else {r.name: r for r in units if r.scheme in {s.name for s in schemes}}
		)
		contracts = _read(
			"Sidra Sale Contract",
			company,
			["name", "signed_on", "currency", "agreed_price", "contract_type", "docstatus"],
			currency=currency,
			docstatus=["in", [1, 2]],
			signed_on=["<=", today],
		)
		self.contracts = None
		self.excluded_contracts = 0
		if contracts is not None and self.units is not None:
			allocations = {}
			for row in _children(
				"Sidra Contract Unit",
				[c.name for c in contracts],
				"Sidra Sale Contract",
				"units",
				["unit", "allocated_price"],
			):
				allocations.setdefault(row.parent, []).append(row)
			self.contracts = []
			for contract in contracts:
				rows = allocations.get(contract.name, [])
				if (
					not rows
					or len({row.unit for row in rows}) != len(rows)
					or any(row.unit not in self.units for row in rows)
				):
					self.excluded_contracts += 1
					continue  # omit whole mixed/inaccessible contracts, never a partial parent value
				if sum((decimal_amount(r.allocated_price) for r in rows), Decimal(0)) != decimal_amount(
					contract.agreed_price
				):
					self.excluded_contracts += 1
					continue
				self.contracts.append(contract)
		self.schedules = None
		if self.contracts is not None:
			parents = {
				c.name: c for c in self.contracts if c.docstatus == 1 and c.contract_type == "Installment"
			}
			self.schedules = _children(
				"Sidra Installment Line",
				parents,
				"Sidra Sale Contract",
				"schedule",
				["due_date", "row_type", "amount"],
				due_date=["between", [today + timedelta(days=1), today + timedelta(days=30)]],
			)
		self.jobs = _read(
			"Sidra Construction Job", company, ["name", "status", "engineer"], currency=currency
		)
		self.stages = (
			None
			if self.jobs is None
			else _children(
				"Sidra Project Stage",
				[j.name for j in self.jobs if j.status in ACTIVE_JOBS],
				"Sidra Construction Job",
				"stages",
				["stage_name", "planned_end", "actual_end", "completion_pct", "engineer"],
			)
		)
		reservations = _read(
			"Sidra Reservation",
			company,
			["name", "unit", "expires_on", "status"],
			status="Active",
			expires_on=["<", today],
		)
		self.reservations = (
			None
			if reservations is None or self.units is None
			else [r for r in reservations if r.unit in self.units]
		)


def _evidence_rows(source, metric, start):
	def row(doctype, record, **values):
		return {"doctype": doctype, "record": record, "currency": source.currency, **values}

	if metric in {"sales_value", "cancelled_contracts"}:
		if source.contracts is None:
			return None
		return [
			row(
				"Sidra Sale Contract",
				c.name,
				date=str(c.signed_on),
				status="Confirmed" if c.docstatus == 1 else "Cancelled",
				value=money(c.agreed_price),
				note="Agreed commercial value; not revenue",
			)
			for c in source.contracts
			if (
				c.docstatus == 1 and getdate(c.signed_on) >= start
				if metric == "sales_value"
				else c.docstatus == 2
			)
		]
	if metric in {"available_units", "inventory_age"}:
		if source.units is None:
			return None
		return [
			row(
				"Sidra Unit",
				u.name,
				date=str(registration_day(u.creation, source.site_timezone)),
				status=u.status,
				value=money(u.cash_price)
				if u.cash_price is not None and decimal_amount(u.cash_price) > 0
				else None,
				age_days=max(0, (source.today - registration_day(u.creation, source.site_timezone)).days),
				note="Current asking price; age since registration, not time in Available status",
			)
			for u in source.units.values()
			if u.status == "Available"
		]
	if metric == "scheduled_dues":
		if source.schedules is None:
			return None
		return [
			row(
				"Sidra Sale Contract",
				r.parent,
				row_reference=r.name,
				date=str(r.due_date),
				status=r.row_type,
				value=money(r.amount),
				note="Gross agreed schedule row before settlements; not unpaid or expected cash",
			)
			for r in source.schedules
		]
	if metric == "stage_exceptions":
		if source.stages is None:
			return None
		jobs = {j.name: j for j in source.jobs}
		return [
			row(
				"Sidra Construction Job",
				r.parent,
				row_reference=r.name,
				date=str(r.planned_end),
				status="Recorded date exception",
				owner=r.engineer or jobs[r.parent].engineer,
				note=r.stage_name
				+ (
					"; actual end " + str(r.actual_end)
					if r.actual_end
					else "; incomplete after recorded planned end"
				),
			)
			for r in source.stages
			if stage_date_exception(r, source.today)
		]
	if metric == "reservations_due":
		if source.reservations is None:
			return None
		return [
			row(
				"Sidra Reservation",
				r.name,
				date=str(r.expires_on),
				status=r.status,
				note="Active reservation past recorded expiry; verify unit state before any action",
			)
			for r in source.reservations
		]
	frappe.throw(_("Unknown executive report metric"))


def executive_snapshot(company, currency, period, now=None):
	if not management_access():
		return unavailable(_("Management reporting access required"))
	if not currency:
		return unavailable(_("Company currency metadata is unavailable"))
	now = now or snapshot_time()
	today = now.date()
	start, _end = period_window(period, today)
	try:
		source = Sources(company, currency, today)
		rows = {key: _evidence_rows(source, key, start) for key in EVIDENCE}
	except ValueError:
		return unavailable(_("An operational source amount or date is invalid; review its source document."))

	def link(metric):
		if not frappe.has_permission("Sidra Sale Contract", "report"):
			return None
		return {
			"path": "/app/query-report/"
			+ quote(REPORT)
			+ "?"
			+ urlencode({"company": company, "period": period, "metric": metric, "as_of": today.isoformat()})
		}

	missing = _("Required source records or linked records are not readable in this Company.")
	metrics = {key: unavailable(FINANCE_REASON) for key in ("cash_collected", "overdue_balance")}
	from sidra_realestate.api.finance_demo_snapshot import demo_financials

	finance = demo_financials(company, currency, start, today)
	if finance is not None:
		for key, value, drilldown, detail in (
			(
				"cash_collected",
				"received",
				"cash_drilldown",
				f"Fictional native Receive Payment Entries posted {start}–{today}; not contract collections.",
			),
			(
				"overdue_balance",
				"overdue",
				"overdue_drilldown",
				"Fictional submitted invoice outstanding amounts, due before today; after native payment allocation. Not contract arrears.",
			),
		):
			metrics[key] = (
				unavailable(finance["reason"])
				if not finance["available"]
				else {
					"available": True,
					"value": finance[value],
					"basis": "native_invoice_demo",
					"detail": detail,
					"drilldown": finance[drilldown],
				}
			)
	sales = rows["sales_value"]
	metrics["sales_value"] = (
		unavailable(missing)
		if sales is None
		else {
			"available": True,
			"value": money(sum((decimal_amount(r["value"]) for r in sales), Decimal(0))),
			"target": None,
			"detail": f"Signed {start}–{today}; {len(sales)} fully permitted, consistent submitted contracts, {currency} only; {source.excluded_contracts} readable source contracts excluded for inaccessible/inconsistent unit allocations. Not revenue.",
			"drilldown": link("sales_value"),
		}
	)
	units = rows["available_units"]
	metrics["available_units"] = (
		unavailable(missing)
		if units is None
		else {
			"available": True,
			"value": len(units),
			"asking_value": money(sum((decimal_amount(r["value"]) for r in units), Decimal(0)))
			if all(r["value"] is not None for r in units)
			else None,
			"detail": "Current, fully permitted units/schemes. Missing or zero price means asking value unverified.",
			"drilldown": link("available_units"),
		}
	)
	schedules = rows["scheduled_dues"]
	metrics["due_next_30_days"] = (
		unavailable(missing)
		if schedules is None
		else {
			"available": True,
			"basis": "gross_schedule",
			"value": money(sum((decimal_amount(r["value"]) for r in schedules), Decimal(0))),
			"detail": f"{today + timedelta(days=1)}–{today + timedelta(days=30)} inclusive; {len(schedules)} schedule rows before settlements. Separate undated down payments excluded.",
			"expected_receipts": unavailable(_("No approved collection forecast")),
			"drilldown": link("scheduled_dues"),
		}
	)
	metrics["projects_on_schedule"] = unavailable(
		_(
			"Recorded stage dates do not establish an approved schedule baseline. Review recorded date exceptions below."
		)
	)

	months = []
	for first in month_starts(today):
		month_sales = (
			None
			if source.contracts is None
			else [
				c
				for c in source.contracts
				if c.docstatus == 1 and getdate(c.signed_on).replace(day=1) == first
			]
		)
		months.append(
			{
				"label": first.strftime("%b %Y")
				+ ("*" if first.month == today.month and first.year == today.year else ""),
				"sales_value": None
				if month_sales is None
				else money(sum((decimal_amount(c.agreed_price) for c in month_sales), Decimal(0))),
				"received": None,
			}
		)
	trends = {
		"available": source.contracts is not None,
		"period_label": "Last six months; *current month to date. Cash series unavailable.",
		"months": months,
		"reason": missing,
	}
	if finance and finance["available"]:
		for first, row in zip(month_starts(today), months, strict=True):
			row["received"] = money(
				sum(
					(
						decimal_amount(r["amount"])
						for r in finance["receipts"]
						if getdate(r["date"]).replace(day=1) == first
					),
					Decimal(0),
				)
			)
		trends["period_label"] = (
			"Last six months; *current month to date. Fictional posted receipts; commercial signed sales are not revenue."
		)

	exposure = []
	for key, label, detail in (
		(
			"stage_exceptions",
			"Recorded stage date exceptions",
			"Current active/on-hold jobs; recorded dates only, not approved baseline performance.",
		),
		(
			"reservations_due",
			"Active reservations past expiry",
			"Current records; no automatic release or cancellation.",
		),
		(
			"cancelled_contracts",
			"Cancelled contract records",
			"Current cancelled records, not cancellations during the selected period.",
		),
	):
		evidence = rows[key]
		exposure.append(
			{
				"label": label,
				"available": evidence is not None,
				"value": len(evidence) if evidence is not None else None,
				"kind": "count",
				"detail": detail,
				"reason": missing,
				"drilldown": link(key) if evidence is not None else None,
			}
		)
	exposure.append(
		{
			"label": "Inventory registration age",
			"available": bool(units),
			"value": median([r["age_days"] for r in units]) if units else None,
			"kind": "count",
			"detail": "Median days since registration of current Available units; not time in Available status.",
			"reason": "No readable available-unit cohort to measure.",
			"drilldown": link("inventory_age") if units else None,
		}
	)
	decisions = []
	for key, action in (
		(
			"stage_exceptions",
			"Review recorded milestone dates and the responsible engineer; no automatic rescheduling.",
		),
		(
			"reservations_due",
			"Review the recorded expiry and unit state through the existing permitted workflow.",
		),
	):
		for r in rows[key] or []:
			decisions.append(
				{
					"id": r.get("row_reference") or r["record"],
					"reference": r["record"],
					"title": "Review " + r["status"].lower()
					if key == "stage_exceptions"
					else "Review reservation past expiry",
					"priority": "attention",
					"priority_label": "Recorded exception",
					"impact": {"description": r["note"]},
					"owner": r.get("owner"),
					"due_date": r["date"],
					"next_action": action,
					"drilldown": {
						"path": "/app/"
						+ {
							"Sidra Construction Job": "sidra-construction-job",
							"Sidra Reservation": "sidra-reservation",
						}[r["doctype"]]
						+ "/"
						+ quote(r["record"], safe="")
					},
				}
			)
	decisions.sort(key=lambda item: (item["due_date"], item["reference"], item["id"]))
	coverage = [rows["stage_exceptions"] is not None, rows["reservations_due"] is not None]
	decision_data = unavailable(missing)
	if any(coverage):
		decision_data = {
			"available": True,
			"total": len(decisions) if all(coverage) else None,
			"items": decisions[:10],
			"summary": ("Partial coverage: an exception source is unreadable. " if not all(coverage) else "")
			+ (
				f"Showing the first 10 of {len(decisions)} recorded exceptions; open the exposure reports for all rows. "
				if len(decisions) > 10
				else ""
			),
		}
	return {
		"available": True,
		"finance_demo": finance,
		"period_label": f"Signed sales {start}–{today}; inventory and exceptions are current records.",
		"freshness": {
			"status": "unknown",
			"label": finance["notice"] + " Native records read now; targets and approved baselines unset."
			if finance and finance["available"]
			else "Operational records read now; Finance, approved targets and baseline completeness are unverified.",
		},
		"metrics": metrics,
		"trends": trends,
		"decisions": decision_data,
		"exposure": {"available": True, "items": exposure},
	}


def executive_evidence(filters):
	"""Called by the native Script Report; each request rechecks role, Company and source permissions."""
	from sidra_realestate.api.staff_dashboard import _companies, _staff_only

	_staff_only()
	if not management_access():
		frappe.throw(_("Management reporting access required"), frappe.PermissionError)
	if not isinstance(filters, dict) or any(
		filters.get(key) is not None and not isinstance(filters[key], str)
		for key in ("company", "period", "metric", "project", "as_of")
	):
		frappe.throw(_("Executive report filters must be text values"))
	company, period, metric = (
		filters.get("company"),
		filters.get("period") or "this_month",
		filters.get("metric") or "sales_value",
	)
	permitted = {c.name: c for c in _companies()}
	if not company or company not in permitted:
		frappe.throw(_("A permitted Company is required"), frappe.PermissionError)
	if not permitted[company].default_currency:
		frappe.throw(_("Company currency metadata is unavailable; no monetary totals can be established"))
	if filters.get("project"):
		frappe.throw(_("Project associations are not configured; choose all permitted projects"))
	if metric not in EVIDENCE:
		frappe.throw(_("Unknown executive report metric"))
	today = snapshot_time().date()
	if filters.get("as_of") and getdate(filters["as_of"]) != today:
		frappe.throw(_("The dashboard date changed. Refresh the dashboard before opening this live report."))
	try:
		start, _end = period_window(period, today)
	except ValueError:
		frappe.throw(_("Unsupported reporting period"))
	try:
		rows = _evidence_rows(Sources(company, permitted[company].default_currency, today), metric, start)
	except ValueError:
		frappe.throw(_("An operational source amount or date is invalid; review its source document."))
	if rows is None:
		frappe.throw(_("The required source records are not readable"), frappe.PermissionError)
	return rows
