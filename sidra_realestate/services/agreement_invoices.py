"""Finance-verified invoice links and read-only accounting from ERPNext."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from sidra_realestate.services.executive_metrics import decimal_amount

MAPPING = "Sidra Agreement Invoice"
INVOICE = "Sales Invoice"
RECEIPT = "Payment Entry"
AGREEMENTS = {"sale": "Sidra Sale Contract", "construction": "Sidra Construction Job"}
APPROVED_JOB_STATES = ("Contracted", "In Progress", "On Hold", "Completed", "Defects Period")


def can_verify():
	return (
		frappe.session.user == "Administrator" or "Accounts Manager" in frappe.get_roles()
	) and frappe.has_permission(INVOICE, "read")


def eligible_agreement(company, kind, name):
	doctype = AGREEMENTS.get(kind)
	if not doctype:
		frappe.throw(_("Choose a sale or construction agreement"))
	filters = {"name": name, "company": company}
	if kind == "sale":
		filters["docstatus"] = 1
	else:
		filters.update(status=["in", APPROVED_JOB_STATES], docstatus=["<", 2])
	if not frappe.get_list(doctype, filters=filters, pluck="name", limit=1):
		frappe.throw(_("Agreement is not available to you"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return doc


def verify_invoice(company, kind, agreement, invoice):
	if not can_verify():
		frappe.throw(_("Only an Accounts Manager can verify invoice links"), frappe.PermissionError)
	target = eligible_agreement(company, kind, agreement)
	if not frappe.get_list(INVOICE, filters={"name": invoice, "company": company}, pluck="name", limit=1):
		frappe.throw(_("Invoice is not available to you"), frappe.PermissionError)
	doc = frappe.get_doc(INVOICE, invoice, for_update=True)
	doc.check_permission("read")
	if (
		doc.docstatus != 1
		or doc.is_return
		or doc.company != target.company
		or doc.customer != target.customer
	):
		frappe.throw(_("Choose a submitted sales invoice for the agreement’s company and customer"))

	existing = frappe.db.get_value(
		MAPPING, {"sales_invoice": invoice}, ["agreement_doctype", "agreement"], as_dict=True
	)
	if existing:
		if existing.agreement_doctype == target.doctype and existing.agreement == target.name:
			return {"invoice": invoice}
		frappe.throw(_("This invoice already has a Finance-verified agreement"))

	link = frappe.new_doc(MAPPING)
	link.update(
		{
			"sales_invoice": invoice,
			"company": company,
			"agreement_doctype": target.doctype,
			"agreement": target.name,
		}
	)
	link.flags.finance_verified = True
	link.insert(ignore_permissions=True)
	return {"invoice": invoice}


def visible_agreements(company, invoices):
	if not invoices:
		return {}
	mappings = frappe.get_all(
		MAPPING,
		filters={"company": company, "sales_invoice": ["in", invoices]},
		fields=["sales_invoice", "agreement_doctype", "agreement"],
	)
	result = {}
	for kind, doctype in AGREEMENTS.items():
		matching = {row.sales_invoice: row.agreement for row in mappings if row.agreement_doctype == doctype}
		if matching and frappe.has_permission(doctype, "read"):
			visible = set(
				frappe.get_list(
					doctype,
					filters={"company": company, "name": ["in", sorted(set(matching.values()))]},
					pluck="name",
					limit=0,
				)
			)
			result.update(
				{
					invoice: {"name": agreement, "type": kind}
					for invoice, agreement in matching.items()
					if agreement in visible
				}
			)
	return result


def account_statement(doc):
	can_read_invoices = frappe.has_permission(INVOICE, "read")
	can_read_receipts = frappe.has_permission(RECEIPT, "read")
	invoices = []
	if can_read_invoices:
		names = frappe.get_all(
			MAPPING,
			filters={"company": doc.company, "agreement_doctype": doc.doctype, "agreement": doc.name},
			pluck="sales_invoice",
		)
		if names:
			invoices = frappe.get_list(
				INVOICE,
				filters={
					"name": ["in", names],
					"company": doc.company,
					"customer": doc.customer,
					"docstatus": 1,
					"is_return": 0,
				},
				fields=["name", "posting_date", "outstanding_amount", "party_account_currency"],
				order_by="posting_date asc, name asc",
				limit=0,
			)
	balances = defaultdict(list)
	for row in invoices:
		if row.party_account_currency:
			balances[row.party_account_currency].append(row.outstanding_amount)
	receipts = _receipts(doc, invoices) if invoices and can_read_receipts else []
	return {
		"can_verify": can_verify(),
		"can_read_invoices": bool(can_read_invoices),
		"can_read_receipts": bool(can_read_receipts),
		"invoices": invoices,
		"balances": [
			{
				"currency": currency,
				"amount": str(sum(decimal_amount(amount) for amount in amounts))
				if all(amount is not None for amount in amounts)
				else None,
			}
			for currency, amounts in sorted(balances.items())
		],
		"receipts": receipts,
	}


def _receipts(doc, invoices):
	allocations = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"parenttype": RECEIPT,
			"parentfield": "references",
			"reference_doctype": INVOICE,
			"reference_name": ["in", [row.name for row in invoices]],
			"allocated_amount": [">", 0],
		},
		fields=["name", "parent", "reference_name", "payment_term", "allocated_amount"],
	)
	if not allocations:
		return []
	receipts = frappe.get_list(
		RECEIPT,
		filters={
			"name": ["in", sorted({row.parent for row in allocations})],
			"company": doc.company,
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": doc.customer,
			"docstatus": 1,
		},
		fields=["name", "posting_date", "paid_from_account_currency"],
		order_by="posting_date asc, name asc",
		limit=0,
	)
	by_receipt = defaultdict(list)
	for row in allocations:
		by_receipt[row.parent].append(row)
	return [
		{
			"id": row.name,
			"receipt": receipt.name,
			"posting_date": receipt.posting_date,
			"currency": receipt.paid_from_account_currency,
			"invoice": row.reference_name,
			"term": row.payment_term,
			"amount": row.allocated_amount,
		}
		for receipt in receipts
		for row in by_receipt[receipt.name]
	]


def validate_installment_allocation(doc, _method=None):
	"""Require a named native term on a new partial receipt for a linked multi-term invoice."""
	if doc.payment_type != "Receive" or doc.party_type != "Customer":
		return
	by_invoice = defaultdict(list)
	for row in doc.references:
		if row.reference_doctype == INVOICE and (row.allocated_amount or 0) > 0:
			by_invoice[row.reference_name].append(row)
	if not by_invoice:
		return

	linked = frappe.get_all(
		MAPPING, filters={"sales_invoice": ["in", list(by_invoice)]}, pluck="sales_invoice"
	)
	for name in linked:
		rows = by_invoice[name]
		invoice = frappe.get_doc(INVOICE, name)
		precision = rows[0].precision("allocated_amount")
		if len(invoice.payment_schedule) < 2 or flt(
			sum(row.allocated_amount for row in rows), precision
		) >= flt(invoice.outstanding_amount, precision):
			continue
		terms = [term.payment_term for term in invoice.payment_schedule]
		use_terms = (
			frappe.get_cached_value(
				"Payment Terms Template",
				invoice.payment_terms_template,
				"allocate_payment_based_on_payment_terms",
			)
			if invoice.payment_terms_template
			else False
		)
		if (
			not use_terms
			or not all(terms)
			or len(set(terms)) != len(terms)
			or any(row.payment_term not in terms for row in rows)
		):
			frappe.throw(
				_(
					"For the partial receipt on linked invoice {0}, select the agreed ERPNext payment term. The invoice must have distinct named terms with term-based allocation enabled."
				).format(name)
			)
