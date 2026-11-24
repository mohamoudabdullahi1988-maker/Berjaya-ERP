from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from sidra_realestate.api.delivery_dashboard import (
	contract_statement,
	find_agreements,
	overdue_installments,
	supplier_payments,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_COMPANY,
	OUTSIDER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_confirmed_contract,
	unique,
)


class TestDeliveryDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_statement_and_lookup_keep_same_customer_contracts_separate(self):
		with as_user("Administrator"):
			first = make_confirmed_contract(unique("_T-STA"), signed_on="2026-10-05")
			second = make_confirmed_contract(unique("_T-STB"), agreed_price=10000)
			self.assertEqual(first.customer, BUYER)
			for doc in (first, second):
				statement = contract_statement(COMPANY, doc.name)
				self.assertEqual((statement["contract"], statement["customer"]), (doc.name, BUYER))
				self.assertEqual(statement["agreed_price"], "10000.00")
				self.assertEqual(len(statement["schedule"]), len(doc.schedule))
				self.assertEqual(statement["schedule"][0]["due_date"], doc.schedule[0].due_date)
			self.assertNotEqual(first.schedule[0].due_date, second.schedule[0].due_date)
			unit_results = find_agreements(COMPANY, first.units[0].unit)
			self.assertEqual([row.name for row in unit_results["contracts"]], [first.name])
			with self.assertRaises(frappe.PermissionError):
				contract_statement(OTHER_COMPANY, first.name)

		with as_user(OUTSIDER):
			for action in (
				lambda: contract_statement(COMPANY, first.name),
				lambda: find_agreements(COMPANY, first.name),
				lambda: overdue_installments(COMPANY),
				lambda: supplier_payments(COMPANY, nowdate(), nowdate()),
			):
				with self.assertRaises(frappe.PermissionError):
					action()

	def test_overdue_keeps_only_positive_past_due_invoice_terms(self):
		today = getdate(nowdate())
		yesterday = today - timedelta(days=1)
		invoice = {
			"voucher_type": "Sales Invoice",
			"voucher_no": "SYN-INVOICE-1",
			"party": BUYER,
			"payment_term": "First installment",
			"due_date": yesterday,
			"outstanding": 75,
		}
		with (
			as_user("Administrator"),
			patch(
				"sidra_realestate.api.delivery_dashboard._run",
				return_value={
					"result": [
						invoice,
						{**invoice, "outstanding": 0},
						{**invoice, "due_date": today},
						{**invoice, "voucher_type": "Journal Entry"},
						{key: value for key, value in invoice.items() if key != "payment_term"},
						None,
					]
				},
			) as native_report,
		):
			report = overdue_installments(COMPANY)
			native_report.assert_called_once_with(
				"Accounts Receivable", {"company": COMPANY, "report_date": str(today)}, payment_terms=True
			)
			self.assertEqual([row["outstanding"] for row in report["rows"]], ["75.00"])

		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			overdue_installments(COMPANY)
