"""Read-only report and agreement lookup for the Berjaya delivery dashboard."""

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from sidra_realestate.api.native_reports import _run
from sidra_realestate.api.staff_dashboard import _companies, _staff_only, money
from sidra_realestate.services.agreement_invoices import (
	AGREEMENTS,
	APPROVED_JOB_STATES,
	account_statement,
	eligible_agreement,
	verify_invoice,
	visible_agreements,
)

CONTRACT = AGREEMENTS["sale"]
JOB = AGREEMENTS["construction"]
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
				"status": ["in", APPROVED_JOB_STATES],
				"docstatus": ["<", 2],
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
	contract_meta = frappe.get_meta(CONTRACT)
	user = frappe.session.user
	if (
		frappe.has_permission(CONTRACT, "read")
		and contract_meta.get_field("units").permlevel
		in contract_meta.get_permlevel_access("read", user=user)
		and "unit"
		in frappe.get_meta("Sidra Contract Unit").get_permitted_fieldnames(parenttype=CONTRACT, user=user)
	):
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
def contract_statement(company, contract, agreement_type="sale"):
	_scope(company)
	doc = eligible_agreement(company, agreement_type, contract)
	frappe.has_permission(doc.doctype, "report", throw=True)
	doc.apply_fieldlevel_read_permissions()
	return {
		"contract": doc.name,
		"agreement_type": agreement_type,
		"customer": doc.customer,
		"currency": doc.currency,
		"signed_on": doc.get("signed_on"),
		"agreed_price": money(
			doc.get("agreed_price") if agreement_type == "sale" else doc.current_contract_value
		),
		"schedule_total": money(doc.get("schedule_total")),
		"schedule": [
			{"due_date": row.due_date, "type": row.row_type, "amount": money(row.amount)}
			for row in doc.get("schedule") or []
		],
		"accounting": account_statement(doc),
	}


@frappe.whitelist(methods=["POST"])
def verify_agreement_invoice(company, agreement_type, agreement, sales_invoice):
	_scope(company)
	return verify_invoice(company, agreement_type, agreement, sales_invoice)


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
		if isinstance(row, dict)
		and row.get("voucher_type") == "Sales Invoice"
		and row.get("voucher_no")
		and "payment_term" in row
		and row.get("due_date")
		and getdate(row["due_date"]) < today
		and row.get("outstanding", 0) > 0
	]
	rows.sort(key=lambda row: (getdate(row["due_date"]), row["invoice"]))
	page = _page(rows[start:], start)
	agreements = visible_agreements(company, sorted({row["invoice"] for row in page["rows"]}))
	for row in page["rows"]:
		row["agreement"] = agreements.get(row["invoice"])
	return {"currency": scope.default_currency, "as_of": today, **page}


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
