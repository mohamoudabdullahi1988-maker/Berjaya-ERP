"""Fictional receipts and statement retries against real ERPNext documents on a test site."""

import io
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate
from openpyxl import Workbook
from pypdf import PdfWriter
from werkzeug.wrappers import Request

from sidra_realestate.api.cashbook import (
	enter_statement_line,
	get_cashbook,
	import_statement,
	list_accounts,
	match_voucher,
	matching_vouchers,
)
from sidra_realestate.api.delivery_dashboard import (
	contract_statement,
	overdue_installments,
	verify_agreement_invoice,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_COMPANY,
	SALES_USER,
	as_user,
	ensure_base_records,
	ensure_user,
	make_confirmed_contract,
	make_contracted_job,
	unique,
)
from sidra_realestate.www.berjaya import get_boot

FINANCE = "cashbook.finance@example.com"
HEADERS = ["Date", "Reference", "Currency", "Deposit", "Withdrawal", "Description"]


def statement_pdf():
	stream = io.BytesIO()
	writer = PdfWriter()
	writer.add_blank_page(width=100, height=100)
	writer.add_metadata({"/Title": "Fictional cashbook statement"})
	writer.write(stream)
	return stream.getvalue()


def uploaded(filename, content):
	request = Request.from_values(method="POST", data={"file": (io.BytesIO(content), filename)})
	return patch.object(frappe.local, "request", request, create=True)


class TestCashbook(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def setUp(self):
		super().setUp()
		self.day = getdate(nowdate())
		self.start = self.day - timedelta(days=1)
		self.period = {"from_date": str(self.start), "to_date": str(self.day)}
		self.company = frappe.get_doc("Company", COMPANY)
		self.parent = frappe.db.get_value(
			"Account", {"company": COMPANY, "root_type": "Asset", "parent_account": ["is", "not set"]}
		)
		with as_user("Administrator"):
			ensure_user(FINANCE, ["Sidra Finance Reviewer", "Accounts Manager", "Accounts User"])
			filters = {"disabled": 0, "year_start_date": ["<=", self.day], "year_end_date": [">=", self.day]}
			if not any(
				not year.companies or COMPANY in {row.company for row in year.companies}
				for year in (
					frappe.get_doc("Fiscal Year", name)
					for name in frappe.get_all("Fiscal Year", filters=filters, pluck="name")
				)
			):
				frappe.get_doc(
					{
						"doctype": "Fiscal Year",
						"year": f"_Test Cashbook {self.day.year}",
						"year_start_date": self.day.replace(month=1, day=1),
						"year_end_date": self.day.replace(month=12, day=31),
						"companies": [{"company": COMPANY}],
					}
				).insert()

	def _account(self, label, kind):
		with as_user("Administrator"):
			account = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": f"_Test Cashbook {label}",
					"company": COMPANY,
					"parent_account": self.parent,
					"account_type": kind,
					"account_currency": "USD",
				}
			).insert()
			if kind == "Bank":
				bank = frappe.get_doc({"doctype": "Bank", "bank_name": f"_Test {label}"}).insert()
				frappe.get_doc(
					{
						"doctype": "Bank Account",
						"account_name": account.account_name,
						"bank": bank.name,
						"company": COMPANY,
						"is_company_account": 1,
						"account": account.name,
					}
				).insert()
		return account.name

	def _record(self, account, reference, *, pay=True, two_terms=False):
		"""The demo's native invoice → get_payment_entry → submit flow with invoice payment terms."""
		with as_user("Administrator"):
			terms = []
			for days in (0, 30) if two_terms else (0,):
				term = frappe.get_doc(
					{
						"doctype": "Payment Term",
						"payment_term_name": f"_Test Installment {reference} {days}",
						"invoice_portion": 50 if two_terms else 100,
						"due_date_based_on": "Day(s) after invoice date",
						"credit_days": days,
					}
				).insert()
				terms.append(
					{
						"payment_term": term.name,
						"invoice_portion": term.invoice_portion,
						"due_date_based_on": term.due_date_based_on,
						"credit_days": days,
					}
				)
			template = frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": f"_Test Terms {reference}",
					"allocate_payment_based_on_payment_terms": 1,
					"terms": terms,
				}
			).insert()
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"_Test Service {reference}",
					"item_group": "All Item Groups",
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			).insert()
			price_list = frappe.get_doc(
				{
					"doctype": "Price List",
					"price_list_name": f"_Test Prices {reference}",
					"currency": "USD",
					"selling": 1,
				}
			).insert()
		with as_user(FINANCE):
			invoice = (
				frappe.get_doc(
					{
						"doctype": "Sales Invoice",
						"company": COMPANY,
						"customer": BUYER,
						"posting_date": self.day,
						"due_date": self.day,
						"currency": "USD",
						"selling_price_list": price_list.name,
						"price_list_currency": "USD",
						"plc_conversion_rate": 1,
						"payment_terms_template": template.name,
						"debit_to": self.company.default_receivable_account,
						"items": [
							{
								"item_code": item.name,
								"qty": 1,
								"rate": 300,
								"income_account": self.company.default_income_account,
								"cost_center": self.company.cost_center,
							}
						],
					}
				)
				.insert()
				.submit()
			)
			if not pay:
				return invoice, None
			payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=account)
			payment.reference_date = self.day
			payment.reference_no = reference
			payment.insert().submit()
		return invoice, payment

	def _import_twice(self, wallet, filename):
		account = self._account(wallet, "Bank")
		reference = f"FICTIONAL-{wallet.upper()}-300"
		invoice, payment = self._record(account, reference)
		row = [str(self.day), reference, "USD", "300", "", "Fictional $300 installment"]
		if filename.endswith(".xlsx"):
			workbook = Workbook()
			workbook.active.append(HEADERS)
			workbook.active.append([self.day, reference, "USD", 300, None, row[-1]])
			stream = io.BytesIO()
			workbook.save(stream)
			content = stream.getvalue()
		else:
			content = (",".join(HEADERS) + "\n" + ",".join(row) + "\n").encode()
		with as_user(FINANCE):
			self.assertIn("cashbook", {item["key"] for item in get_boot()["nav"]})
			self.assertIn(account, {row.name for row in list_accounts(COMPANY)})
			with uploaded(filename, content):
				self.assertEqual(import_statement(COMPANY, account), {"created": 1, "duplicates": 0})
			book = get_cashbook(COMPANY, account, **self.period)
			self.assertEqual(len(book["statement"]["lines"]), 1)
			transaction = book["statement"]["lines"][0].name
			candidates = matching_vouchers(COMPANY, account, transaction, **self.period)
			self.assertEqual(
				[(row["name"], row["reference"], row["can_match"]) for row in candidates],
				[(payment.name, reference, True)],
			)
			self.assertEqual(
				match_voucher(COMPANY, account, transaction, "Payment Entry", payment.name, **self.period),
				{"status": "Reconciled"},
			)
			with uploaded(filename, content):
				self.assertEqual(import_statement(COMPANY, account), {"created": 0, "duplicates": 1})
			self.assertEqual(
				match_voucher(COMPANY, account, transaction, "Payment Entry", payment.name, **self.period),
				{"status": "Reconciled"},
			)
			book = get_cashbook(COMPANY, account, observed_balance="300", **self.period)

		self.assertEqual(
			[Decimal(book[key]) for key in ("opening", "receipts", "payments", "closing", "difference")],
			[0, 300, 0, 300, 0],
		)
		self.assertEqual(
			[(row["voucher_no"], Decimal(row["balance"])) for row in book["movements"]], [(payment.name, 300)]
		)
		self.assertEqual(book["statement"]["lines"], [])
		self.assertEqual(frappe.db.count("Bank Transaction", {"reference_number": reference}), 1)
		transaction = frappe.get_doc("Bank Transaction", transaction)
		self.assertEqual(
			[(row.payment_entry, row.allocated_amount) for row in transaction.payment_entries],
			[(payment.name, 300)],
		)
		self.assertEqual(frappe.db.count("Payment Entry", {"company": COMPANY, "paid_to": account}), 1)
		installments = invoice.reload().payment_schedule
		self.assertEqual([(row.paid_amount, row.outstanding) for row in installments], [(300, 0)])
		self.assertEqual(
			[(row.reference_name, row.allocated_amount) for row in payment.reload().references],
			[(invoice.name, 300)],
		)
		self.assertEqual(getdate(payment.clearance_date), self.day)

	def test_verified_agreements_for_one_customer_use_only_their_own_receipts(self):
		account = self._account("Agreement receipt", "Bank")
		with as_user("Administrator"):
			contract = make_confirmed_contract(unique("_T-LNK"))
			job = make_contracted_job()
		first, _ = self._record(account, "AGREEMENT-SALE", pay=False, two_terms=True)
		second, _ = self._record(account, "AGREEMENT-JOB", pay=False)
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			verify_agreement_invoice(COMPANY, "sale", contract.name, first.name)

		with as_user(FINANCE):
			self.assertEqual(contract_statement(COMPANY, contract.name)["accounting"]["balances"], [])
			verify_agreement_invoice(COMPANY, "sale", contract.name, first.name)
			verify_agreement_invoice(COMPANY, "sale", contract.name, first.name)
			with self.assertRaises(frappe.ValidationError):
				verify_agreement_invoice(COMPANY, "construction", job.name, first.name)
			with self.assertRaises(frappe.PermissionError):
				verify_agreement_invoice(OTHER_COMPANY, "sale", contract.name, second.name)
			verify_agreement_invoice(COMPANY, "construction", job.name, second.name)
			self.assertEqual(
				frappe.db.get_value("Sidra Agreement Invoice", {"sales_invoice": first.name}, "owner"),
				FINANCE,
			)
			pe = get_payment_entry("Sales Invoice", first.name, bank_account=account)
			term = first.payment_schedule[1].payment_term
			selected = next(row.as_dict() for row in pe.references if row.payment_term == term)
			selected["allocated_amount"] = 80
			pe.set("references", [selected])
			pe.paid_amount = pe.received_amount = 80
			pe.reference_date = self.day
			pe.reference_no = "AGREEMENT-PARTIAL"
			pe.insert().submit()

			sale = contract_statement(COMPANY, contract.name)["accounting"]
			build = contract_statement(COMPANY, job.name, "construction")["accounting"]
			self.assertEqual([Decimal(row["amount"]) for row in sale["balances"]], [220])
			self.assertEqual([Decimal(row["amount"]) for row in build["balances"]], [300])
			self.assertEqual(
				[(row["receipt"], row["term"], Decimal(str(row["amount"]))) for row in sale["receipts"]],
				[(pe.name, term, 80)],
			)
			self.assertEqual(build["receipts"], [])
			first.reload()
			self.assertEqual([row.outstanding for row in first.payment_schedule], [150, 70])

		with as_user(SALES_USER):
			protected = contract_statement(COMPANY, contract.name)["accounting"]
			self.assertFalse(protected["can_verify"])
			self.assertEqual(protected["receipts"], [])

	def test_overdue_report_uses_posted_invoice_terms(self):
		account = self._account("Overdue", "Bank")
		unpaid, _ = self._record(account, "REPORT-UNPAID", pay=False)
		paid, _ = self._record(account, "REPORT-PAID")
		tomorrow = self.day + timedelta(days=1)
		with (
			as_user(FINANCE),
			patch("sidra_realestate.api.delivery_dashboard.nowdate", return_value=str(tomorrow)),
		):
			report = overdue_installments(COMPANY)
		rows = {row["invoice"]: row["outstanding"] for row in report["rows"]}
		self.assertEqual(rows[unpaid.name], "300.00")
		self.assertNotIn(paid.name, rows)

	def test_zaad_csv_import_is_idempotent(self):
		self._import_twice("ZAAD", "fictional-zaad.csv")

	def test_edahab_excel_import_is_idempotent(self):
		self._import_twice("eDahab", "fictional-edahab.xlsx")

	def test_cash_variance_uses_the_posted_ledger(self):
		cash = self._account("Till", "Cash")
		with as_user(FINANCE):
			equity = frappe.db.get_value(
				"Account", {"company": COMPANY, "root_type": "Equity", "is_group": 0}
			)
			journal = (
				frappe.get_doc(
					{
						"doctype": "Journal Entry",
						"company": COMPANY,
						"posting_date": self.start - timedelta(days=1),
						"accounts": [
							{"account": cash, "debit_in_account_currency": 100},
							{"account": equity, "credit_in_account_currency": 100},
						],
					}
				)
				.insert()
				.submit()
			)
			book = get_cashbook(COMPANY, cash, observed_balance="90", **self.period)
			self.assertEqual(Decimal(book["opening"]), 100)
			self.assertEqual(Decimal(book["closing"]), 100)
			self.assertEqual(Decimal(book["difference"]), -10)
			self.assertIsNone(book["statement"])
			self.assertEqual(journal.docstatus, 1)

	def test_manual_pdf_evidence_is_private_and_retry_safe(self):
		account = self._account("Manual Bank", "Bank")
		pdf = statement_pdf()
		with as_user(FINANCE):
			with uploaded("fictional.pdf", pdf):
				first = enter_statement_line(
					COMPANY, account, str(self.day), "FICTIONAL-MANUAL", withdrawal="20"
				)
			with uploaded("fictional.pdf", pdf):
				second = enter_statement_line(
					COMPANY, account, str(self.day), "FICTIONAL-MANUAL", withdrawal="20"
				)
		self.assertTrue(first["created"])
		self.assertEqual(second, {"name": first["name"], "created": False})
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Bank Transaction", "attached_to_name": first["name"]},
			fields=["name", "is_private"],
		)
		self.assertEqual(len(files), 1)
		self.assertEqual(files[0].is_private, 1)
		evidence = frappe.get_doc("File", files[0].name)
		self.assertEqual(Path(evidence.get_full_path()).read_bytes(), pdf)
		with as_user(SALES_USER):
			self.assertFalse(evidence.has_permission("read"))

	def test_sales_role_and_wrong_company_are_denied(self):
		account = self._account("Restricted Bank", "Bank")
		with as_user(SALES_USER):
			self.assertNotIn("cashbook", {item["key"] for item in get_boot()["nav"]})
			for method, args in (
				(list_accounts, (COMPANY,)),
				(get_cashbook, (COMPANY, account, str(self.start), str(self.day))),
				(import_statement, (COMPANY, account)),
				(enter_statement_line, (COMPANY, account, str(self.day), "FICTIONAL")),
				(matching_vouchers, (COMPANY, account, "unknown", str(self.start), str(self.day))),
				(
					match_voucher,
					(COMPANY, account, "unknown", "Payment Entry", "unknown", str(self.start), str(self.day)),
				),
			):
				with self.subTest(method=method.__name__), self.assertRaises(frappe.PermissionError):
					method(*args)
		with as_user(FINANCE), self.assertRaises(frappe.PermissionError):
			get_cashbook(OTHER_COMPANY, account, **self.period)

	def test_company_user_permission_blocks_the_ledger(self):
		account = self._account("Other Company Permission", "Cash")
		permission = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": FINANCE,
				"allow": "Company",
				"for_value": OTHER_COMPANY,
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.clear_cache(user=FINANCE)
		try:
			with as_user(FINANCE), self.assertRaises(frappe.PermissionError):
				get_cashbook(COMPANY, account, **self.period)
		finally:
			frappe.delete_doc("User Permission", permission.name)
			frappe.clear_cache(user=FINANCE)
