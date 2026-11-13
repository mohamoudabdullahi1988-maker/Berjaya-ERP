"""Real native vouchers and reports on the disposable CI site, never mock ledger balances."""

import hashlib
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from sidra_realestate.api.finance_demo_snapshot import demo_financials
from sidra_realestate.api.staff_dashboard import get_dashboard
from sidra_realestate.finance_demo import (
	ACCOUNT_PREFIX,
	COMPANY,
	CUSTOMER,
	EXPECTED,
	FLAGS,
	SCHEME,
	VOUCHERS,
	_fiscal_year,
	create_finance_demo_data,
	report_links,
	verify_finance_demo,
)
from sidra_realestate.tests.helpers import (
	GENERAL_MANAGER,
	OTHER_COMPANY,
	as_user,
	ensure_base_records,
	ensure_company,
	ensure_user,
)

EXISTING_SCHEME = "_TEST-SH-EXISTING"
EXISTING_UNITS = 60


def existing_units():
	"""Count and checksum of every field of the Company's own units (brief 1.4)."""
	rows = frappe.get_all(
		"Sidra Unit",
		filters={"company": COMPANY, "scheme": ("!=", SCHEME)},
		fields=["*"],
		order_by="name asc",
		limit_page_length=0,
	)
	return len(rows), hashlib.sha256(frappe.as_json(rows).encode()).hexdigest()


def ensure_existing_units():
	if not frappe.db.exists("Sidra Scheme", EXISTING_SCHEME):
		frappe.get_doc(
			{
				"doctype": "Sidra Scheme",
				"scheme_code": EXISTING_SCHEME,
				"scheme_name": "_Test existing plots",
				"company": COMPANY,
			}
		).insert()
		for index in range(1, EXISTING_UNITS + 1):
			frappe.get_doc(
				{
					"doctype": "Sidra Unit",
					"unit_code": f"{EXISTING_SCHEME}-{index:02d}",
					"scheme": EXISTING_SCHEME,
					"unit_type": "Plot",
					"cash_price": 10000,
				}
			).insert()
		frappe.db.commit()


def demo_masters():
	return (
		frappe.db.count("Account", {"company": COMPANY, "account_name": ("like", ACCOUNT_PREFIX + "%")}),
		frappe.db.count("Customer", {"customer_name": CUSTOMER}),
		frappe.db.count("Sidra Scheme", {"scheme_code": SCHEME}),
		frappe.db.count("File", {"attached_to_doctype": "Company", "attached_to_name": COMPANY}),
	)


class TestFinanceDemo(IntegrationTestCase):
	def test_guarded_dataset_native_reports_dashboard_and_repeat(self):
		ensure_base_records()
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			# The loader never creates its Company.
			if not frappe.db.exists("Company", COMPANY):
				with self.assertRaisesRegex(frappe.ValidationError, "does not exist"):
					create_finance_demo_data()
			ensure_company(COMPANY, "SH")
			ensure_existing_units()
		units_before = existing_units()
		self.assertEqual(units_before[0], EXISTING_UNITS)
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 0 for flag in FLAGS}):
			before = frappe.db.count("GL Entry")
			with self.assertRaises(frappe.ValidationError):
				create_finance_demo_data()
			self.assertEqual(frappe.db.count("GL Entry"), before)

		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			# Posting failure must leave neither Company nor any partial ledger behind.
			with patch(
				"sidra_realestate.finance_demo._operational", side_effect=RuntimeError("test rollback")
			):
				with self.assertRaisesRegex(RuntimeError, "test rollback"):
					create_finance_demo_data()
			self.assertEqual(demo_masters(), (0, 0, 0, 0))
			self.assertEqual(frappe.db.count("GL Entry"), before)
			self.assertEqual(existing_units(), units_before)

			self._foreign_gl_refused()
			# An unreadable manifest is a refusal, never a clean slate.
			with patch(
				"sidra_realestate.finance_demo.frappe.get_all", side_effect=RuntimeError("unreadable")
			):
				with self.assertRaisesRegex(frappe.ValidationError, "manifest"):
					create_finance_demo_data()
			self.assertEqual(frappe.db.count("GL Entry"), before)

			with patch("frappe.get_print", side_effect=AssertionError("No document generation in demo")):
				data = create_finance_demo_data()
			self.assertTrue(data["created"])
			self.assertEqual(existing_units(), units_before, "the Company's own units must not change")
			self.assertEqual(verify_finance_demo()["debits"], "237000.00")
			self.assertEqual(verify_finance_demo()["credits"], "237000.00")
			before_repeat = frappe.db.count("GL Entry")
			second = create_finance_demo_data()
			self.assertFalse(second["created"])
			self.assertEqual(data["vouchers"], second["vouchers"])
			self.assertEqual(frappe.db.count("GL Entry"), before_repeat)
			self.assertEqual(existing_units(), units_before)
			for dt, count in VOUCHERS.items():
				self.assertEqual(frappe.db.count(dt, {"company": COMPANY, "docstatus": 1}), count)
			self.assertEqual(
				sorted(
					frappe.get_all("Sales Invoice", filters={"company": COMPANY}, pluck="outstanding_amount")
				),
				[0, 15000, 20000],
			)
			self.assertEqual(
				sorted(
					frappe.get_all(
						"Purchase Invoice", filters={"company": COMPANY}, pluck="outstanding_amount"
					)
				),
				[0, 8000],
			)
			self._native_reports(data)
			self._reopened_capture(data)
			self._dashboard(data)
			self.assertEqual(
				frappe.db.count("GL Entry"), before_repeat, "Read-only dashboard/reports must not post"
			)
			# Cancelled or incomplete vouchers are not silently recreated.
			with patch("sidra_realestate.finance_demo.frappe.get_all", return_value=[]):
				with self.assertRaises(frappe.ValidationError):
					verify_finance_demo(data)

	def _foreign_gl_refused(self):
		"""One voucher the manifest does not own: refuse, name the count, write nothing (G14)."""
		before = (frappe.db.count("GL Entry"), demo_masters(), existing_units())
		frappe.db.savepoint("foreign_gl")
		try:
			_fiscal_year(frappe.utils.getdate())
			cash = frappe.get_all(
				"Account", filters={"company": COMPANY, "is_group": 0, "account_type": "Cash"}, pluck="name"
			)[0]
			equity = frappe.get_all(
				"Account", filters={"company": COMPANY, "is_group": 0, "root_type": "Equity"}, pluck="name"
			)[0]
			foreign = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"company": COMPANY,
					"voucher_type": "Journal Entry",
					"posting_date": frappe.utils.getdate(),
					"accounts": [
						{"account": cash, "debit_in_account_currency": 7},
						{"account": equity, "credit_in_account_currency": 7},
					],
				}
			).insert()
			foreign.submit()
			seeded = (frappe.db.count("GL Entry"), demo_masters())
			with self.assertRaisesRegex(
				frappe.ValidationError,
				f"has 2 GL entries not owned by the finance demo manifest .first: Journal Entry {foreign.name}",
			):
				create_finance_demo_data()
			self.assertEqual((frappe.db.count("GL Entry"), demo_masters()), seeded, "nothing was written")
			self.assertEqual(frappe.db.count("Journal Entry", {"company": COMPANY}), 1)
		finally:
			frappe.db.rollback(save_point="foreign_gl")
			frappe.cache.delete_value("fiscal_years")
		self.assertEqual((frappe.db.count("GL Entry"), demo_masters(), existing_units()), before)

	def _native_reports(self, data):
		from erpnext.accounts.report.accounts_payable.accounts_payable import execute as payable
		from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as receivable
		from erpnext.accounts.report.balance_sheet.balance_sheet import execute as balance_sheet
		from erpnext.accounts.report.financial_statements import build_period_list
		from erpnext.accounts.report.general_ledger.general_ledger import execute as general_ledger
		from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
			execute as profit_loss,
		)
		from erpnext.accounts.report.trial_balance.trial_balance import execute as trial_balance

		filters = frappe._dict(company=COMPANY, from_date=data["from_date"], to_date=data["as_of"])
		gl = general_ledger(filters)[1]
		# Voucher rows only: native report also includes opening/closing total rows.
		rows = [r for r in gl if r.get("voucher_no")]
		self.assertEqual(sum(Decimal(str(r.get("debit", 0))) for r in rows), Decimal("237000"))
		self.assertEqual(sum(Decimal(str(r.get("credit", 0))) for r in rows), Decimal("237000"))
		for run, expected in ((receivable, "35000"), (payable, "8000")):
			result = run(
				frappe._dict(company=COMPANY, report_date=data["as_of"], ageing_based_on="Due Date")
			)[1]
			voucher_rows = [r for r in result if r.get("voucher_no")]
			self.assertEqual(
				sum(Decimal(str(r.get("outstanding") or 0)) for r in voucher_rows),
				Decimal(expected),
				run.__module__,
			)
		statement_filters = frappe._dict(
			company=COMPANY,
			filter_based_on="Date Range",
			period_start_date=data["from_date"],
			period_end_date=data["as_of"],
			periodicity="Yearly",
			presentation_currency="USD",
		)
		periods = build_period_list(statement_filters)
		for run, labels in (
			(profit_loss, ("Revenue", "Expenses")),
			(balance_sheet, ("Bank", "Receivables", "Payables", "Capital")),
		):
			result = run(statement_filters.copy())[1]
			for label in labels:
				account = data["accounts"][label]
				row = next(r for r in result if r.get("account") == account)
				keys = [p.key for p in periods] if run == profit_loss else [periods[-1].key]
				amount = sum(Decimal(str(row.get(key) or 0)) for key in keys)
				self.assertEqual(amount, abs(Decimal(EXPECTED[label])), f"{run.__module__}: {label}")
		# Native TB is one fiscal year at a time. Across New Year, inspect each year separately.
		for year_name in data["fiscal_years"]:
			year = frappe.get_doc("Fiscal Year", year_name)
			tb = trial_balance(
				frappe._dict(
					company=COMPANY,
					fiscal_year=year_name,
					from_date=max(getdate(data["from_date"]), getdate(year.year_start_date)),
					to_date=min(getdate(data["as_of"]), getdate(year.year_end_date)),
					show_zero_values=0,
					include_default_book_entries=1,
				)
			)[1]
			leaves = [r for r in tb if r.get("account") in data["accounts"].values()]
			self.assertTrue(leaves)
			self.assertEqual(
				sum(Decimal(str(r.get("debit") or 0)) for r in leaves),
				sum(Decimal(str(r.get("credit") or 0)) for r in leaves),
			)
		self.assertEqual(
			set(report_links(data)),
			{
				"General Ledger",
				"Trial Balance",
				"Profit and Loss Statement",
				"Balance Sheet",
				"Accounts Receivable",
				"Accounts Payable",
			},
		)

	def _reopened_capture(self, data):
		contract = frappe.get_doc("Sidra Sale Contract", data["operational"]["contract"])
		attachment = frappe.get_doc("File", data["operational"]["attachment"])
		self.assertEqual(contract.docstatus, 1)
		self.assertEqual(contract.source, "External (registered)")
		self.assertEqual(contract.signed_copy, attachment.file_url)
		self.assertEqual(attachment.attached_to_name, contract.name)
		self.assertTrue(attachment.is_private)
		self.assertIn("FICTIONAL DEMO ORIGINAL", attachment.get_content())
		self.assertEqual([r.amount for r in contract.schedule], [10000, 10000, 10000])
		self.assertEqual(contract.schedule_difference, 0)
		self.assertEqual(contract.terms_approved_by, "Administrator")

	def _dashboard(self, data):
		today = getdate(data["as_of"])
		financials = demo_financials(COMPANY, "USD", date(today.year, today.month, 1), today)
		self.assertTrue(financials["available"], financials)
		self.assertEqual(financials["received"], "35000.00")
		self.assertEqual(financials["overdue"], "15000.00")
		self.assertEqual(financials["overdue_invoices"], 1)
		self.assertEqual(financials["collection_rate"], 70)
		self.assertEqual(financials["aging"][0]["amount"], "15000.00")
		self.assertIsNone(demo_financials(OTHER_COMPANY, "USD", today, today))
		self.assertFalse(demo_financials(COMPANY, "SOS", today, today)["available"])
		with as_user(GENERAL_MANAGER):
			self.assertFalse(
				demo_financials(COMPANY, "USD", today, today)["available"],
				"GM role alone must not grant financial reads",
			)
			with self.assertRaises(frappe.PermissionError):
				create_finance_demo_data()
		original = frappe.get_list

		def incomplete(doctype, *args, **kwargs):
			rows = original(doctype, *args, **kwargs)
			return rows[:-1] if doctype == "Sales Invoice" else rows

		with patch("sidra_realestate.api.finance_demo_snapshot.frappe.get_list", side_effect=incomplete):
			self.assertFalse(demo_financials(COMPANY, "USD", today, today)["available"])
		finance_user = ensure_user(
			"sidra.finance-demo-test@example.com", ["Accounts Manager", "Sidra General Manager"]
		)
		with as_user(finance_user):
			self.assertTrue(demo_financials(COMPANY, "USD", today, today)["available"])
		operational_finance_user = ensure_user(
			"sidra.finance-operations-test@example.com", ["Accounts Manager", "Sidra Finance Reviewer"]
		)
		with as_user(operational_finance_user):
			operational = get_dashboard(company=COMPANY)
			self.assertFalse(operational["executive"]["available"])
			self.assertTrue(operational["payments"]["available"], operational["payments"])
		permission = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": finance_user,
				"allow": "Company",
				"for_value": OTHER_COMPANY,
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.clear_cache(user=finance_user)
		try:
			with as_user(finance_user):
				self.assertFalse(demo_financials(COMPANY, "USD", today, today)["available"])
				with self.assertRaises(frappe.PermissionError):
					get_dashboard(company=COMPANY)
		finally:
			frappe.delete_doc("User Permission", permission.name)
		dashboard = get_dashboard(company=COMPANY)
		self.assertEqual(dashboard["payments"]["basis"], "native_invoice_demo")
		self.assertEqual(dashboard["payments"]["overdue_contracts"], None)
		metrics = dashboard["executive"]["metrics"]
		self.assertEqual(metrics["cash_collected"]["value"], "35000.00")
		self.assertEqual(metrics["overdue_balance"]["value"], "15000.00")
		self.assertEqual(metrics["sales_value"]["value"], "30000.00")
		self.assertEqual(metrics["due_next_30_days"]["value"], "10000.00")
		self.assertEqual(metrics["available_units"]["value"], EXISTING_UNITS + 2)
		self.assertEqual(dashboard["jobs"]["active"], 1)
		self.assertEqual(dashboard["jobs"]["overdue_milestones"], 1)
