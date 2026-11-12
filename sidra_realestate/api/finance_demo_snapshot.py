"""Read native finance only for the opted-in finance demo Company and its owned vouchers (G13)."""

import json
from decimal import Decimal
from urllib.parse import quote, urlencode

import frappe
from frappe.utils import getdate

from sidra_realestate.finance_demo import COMPANY, _manifest, enabled
from sidra_realestate.services.executive_metrics import decimal_amount, money


def demo_financials(company, currency, start, today):
	if not enabled(company):
		return None  # Production Finance gate remains closed.
	missing = {
		"available": False,
		"reason": "Fictional finance demo requires complete readable native invoices and payments.",
	}
	if currency != "USD" or not all(
		frappe.has_permission(dt, "read") for dt in ("Sales Invoice", "Payment Entry")
	):
		return missing
	try:
		data = _manifest()
		invoices = frappe.get_list(
			"Sales Invoice",
			filters={"company": COMPANY, "docstatus": 1},
			fields=["name", "currency", "posting_date", "due_date", "grand_total", "outstanding_amount"],
			limit_page_length=0,
		)
		payments = frappe.get_list(
			"Payment Entry",
			filters={"company": COMPANY, "docstatus": 1},
			fields=[
				"name",
				"payment_type",
				"posting_date",
				"paid_to",
				"paid_to_account_currency",
				"base_received_amount",
			],
			limit_page_length=0,
		)
		if (
			{r.name for r in invoices} != set(data["vouchers"]["Sales Invoice"])
			or {r.name for r in payments} != set(data["vouchers"]["Payment Entry"])
			or any(
				r.currency != "USD"
				or r.grand_total is None
				or r.outstanding_amount is None
				or not r.due_date
				or not r.posting_date
				or getdate(r.posting_date) > today
				for r in invoices
			)
			or any(
				not r.posting_date
				or getdate(r.posting_date) > today
				or r.payment_type not in ("Receive", "Pay")
				or r.base_received_amount is None
				for r in payments
			)
			or getdate(data["as_of"]) > today
		):
			return missing
		receipts = [r for r in payments if r.payment_type == "Receive"]
		if any(
			r.paid_to != data["accounts"]["Bank"] or r.paid_to_account_currency != "USD" for r in receipts
		):
			return missing
		if any(
			decimal_amount(r.outstanding_amount) < 0
			or decimal_amount(r.outstanding_amount) > decimal_amount(r.grand_total)
			for r in invoices
		):
			return missing
		due = [r for r in invoices if getdate(r.due_date) <= today]
		overdue = [r for r in due if getdate(r.due_date) < today and decimal_amount(r.outstanding_amount) > 0]
		cohort = sum((decimal_amount(r.grand_total) for r in due), Decimal(0))
		unpaid = sum((decimal_amount(r.outstanding_amount) for r in due), Decimal(0))
		received = sum(
			(
				decimal_amount(r.base_received_amount)
				for r in receipts
				if start <= getdate(r.posting_date) <= today
			),
			Decimal(0),
		)
		aging = []
		for label, first, last in (
			("1–30 days", 1, 30),
			("31–60 days", 31, 60),
			("61–90 days", 61, 90),
			("90+ days", 91, 999999),
		):
			aging.append(
				{
					"label": label,
					"amount": money(
						sum(
							(
								decimal_amount(r.outstanding_amount)
								for r in overdue
								if first <= (today - getdate(r.due_date)).days <= last
							),
							Decimal(0),
						)
					),
				}
			)

		def link(report, **filters):
			return {
				"path": "/app/query-report/"
				+ quote(report)
				+ "?"
				+ urlencode({"company": COMPANY, **filters})
			}

		return {
			"available": True,
			"basis": "native_invoice_demo",
			"notice": data["notice"],
			"received": money(received),
			"overdue": money(sum((decimal_amount(r.outstanding_amount) for r in overdue), Decimal(0))),
			"collection_rate": float((cohort - unpaid) / cohort * 100) if cohort else None,
			"overdue_invoices": len(overdue),
			"overdue_contracts": None,
			"aging": aging,
			"receipts": [
				{"date": str(r.posting_date), "amount": money(r.base_received_amount)} for r in receipts
			],
			"cash_drilldown": {
				"path": "/app/payment-entry?"
				+ urlencode(
					{
						"company": COMPANY,
						"docstatus": 1,
						"payment_type": "Receive",
						"posting_date": json.dumps(["between", [str(start), str(today)]]),
					}
				)
			},
			"overdue_drilldown": link("Accounts Receivable", report_date=today),
		}
	except (
		OSError,
		frappe.ValidationError,
		frappe.PermissionError,
		frappe.DoesNotExistError,
		ValueError,
		KeyError,
		TypeError,
	):
		return missing
