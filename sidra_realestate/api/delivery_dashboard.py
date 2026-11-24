"""Read-only report and agreement lookup for the Berjaya delivery dashboard."""

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from sidra_realestate.api.native_reports import _run
from sidra_realestate.api.staff_dashboard import _companies, _staff_only, money

CONTRACT = "Sidra Sale Contract"
JOB = "Sidra Construction Job"
PAGE_LENGTH = 50


def _scope(company):
	_staff_only()
	for row in _companies():
		if row.name == company:
			return row
	frappe.throw(_("Company is not available to you"), frappe.PermissionError)


def _page(rows, start):
	return {
		"rows": rows[:PAGE_LENGTH],
		"has_more": len(rows) > PAGE_LENGTH,
		"next_start": start + PAGE_LENGTH,
	}


@frappe.whitelist(methods=["GET"])
def find_agreements(company, text):
	_scope(company)
	text = (text or "").strip()
	if not 2 <= len(text) <= 100:
		frappe.throw(_("Enter between 2 and 100 characters"))
	escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	pattern = f"%{escaped}%"
	customers = []
	if frappe.has_permission("Customer", "read"):
		fields = frappe.get_meta("Customer").get_permitted_fieldnames(user=frappe.session.user)
		matches = [["name", "like", pattern]]
		matches.extend(
			[field, "like", pattern] for field in ("customer_name", "mobile_no") if field in fields
		)
		customers = frappe.get_list("Customer", or_filters=matches, pluck="name", limit_page_length=0)

	def find(doctype, references, additional=None):
		if not frappe.has_permission(doctype, "read"):
			return []
		filters = (
			{"company": company, "docstatus": 1}
			if doctype == CONTRACT
			else {
				"company": company,
				"status": ["in", ["Contracted", "In Progress", "On Hold", "Completed", "Defects Period"]],
			}
		)
		permitted = frappe.get_meta(doctype).get_permitted_fieldnames(user=frappe.session.user)
		match = [["name", "like", pattern]]
		match.extend([field, "like", pattern] for field in references if field in permitted)
		if customers and "customer" in permitted:
			match.append(["customer", "in", customers])
		if additional:
			match.append(additional)
		return frappe.get_list(
			doctype,
			filters=filters,
			or_filters=match,
			fields=["name", "customer", *references],
			order_by="name asc",
			page_length=PAGE_LENGTH,
		)

	unit_filter = None
	if frappe.has_permission(CONTRACT, "read") and "units" in frappe.get_meta(
		CONTRACT
	).get_permitted_fieldnames(user=frappe.session.user):
		# Only return matching parent records after Frappe applies their permissions below.
		parents = frappe.get_all(
			"Sidra Contract Unit",
			filters={"parenttype": CONTRACT, "parentfield": "units", "unit": ["like", pattern]},
			pluck="parent",
			distinct=True,
		)
		if parents:
			unit_filter = ["name", "in", parents]
	return {
		"contracts": find(CONTRACT, ("external_reference",), unit_filter),
		"jobs": find(JOB, ("project",)),
		"can_open_payments": frappe.has_permission("Payment Entry", "read"),
	}


@frappe.whitelist(methods=["GET"])
def contract_statement(company, contract):
	_scope(company)
	frappe.has_permission(CONTRACT, "report", throw=True)
	if not frappe.get_list(
		CONTRACT, filters={"name": contract, "company": company, "docstatus": 1}, pluck="name", page_length=1
	):
		frappe.throw(_("Contract is not available to you"), frappe.PermissionError)
	doc = frappe.get_doc(CONTRACT, contract)
	doc.check_permission("read")
	doc.apply_fieldlevel_read_permissions()
	return {
		"contract": doc.name,
		"customer": doc.customer,
		"currency": doc.currency,
		"signed_on": doc.signed_on,
		"agreed_price": money(doc.agreed_price),
		"schedule_total": money(doc.schedule_total),
		"schedule": [
			{"due_date": row.due_date, "type": row.row_type, "amount": money(row.amount)}
			for row in doc.get("schedule") or []
		],
	}


@frappe.whitelist(methods=["GET"])
def overdue_installments(company, start=0):
	scope = _scope(company)
	today = getdate(nowdate())
	start = max(0, cint(start))
	data = _run("Accounts Receivable", {"company": company, "report_date": str(today)}, payment_terms=True)
	rows = [
		{
			"invoice": row.get("voucher_no"),
			"customer": row.get("party"),
			"term": row.get("payment_term"),
			"due_date": row["due_date"],
			"outstanding": money(row["outstanding"]),
		}
		for row in data.get("result") or []
		if row
		and row.get("voucher_type") == "Sales Invoice"
		and "payment_term" in row
		and row.get("due_date")
		and getdate(row["due_date"]) < today
		and row.get("outstanding", 0) > 0
	]
	rows.sort(key=lambda row: (getdate(row["due_date"]), row["invoice"]))
	return {"currency": scope.default_currency, "as_of": today, **_page(rows[start:], start)}


@frappe.whitelist(methods=["GET"])
def supplier_payments(company, from_date, to_date, start=0):
	_scope(company)
	frappe.has_permission("Payment Entry", "report", throw=True)
	from_date, to_date = getdate(from_date), getdate(to_date)
	if from_date > to_date:
		frappe.throw(_("From date must be on or before To date"))
	start = max(0, cint(start))
	rows = frappe.get_list(
		"Payment Entry",
		filters={
			"company": company,
			"docstatus": 1,
			"party_type": "Supplier",
			"payment_type": "Pay",
			"posting_date": ["between", [from_date, to_date]],
		},
		fields=["name", "party", "posting_date", "paid_amount", "paid_from_account_currency"],
		order_by="posting_date desc, name asc",
		start=start,
		page_length=PAGE_LENGTH + 1,
	)
	return _page(rows, start)
