"""Account-currency cashbook and statement reconciliation on native ERPNext records."""

import csv
import io
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

import frappe
from erpnext.accounts.doctype.bank_reconciliation_tool import bank_reconciliation_tool as reconciliation
from frappe import _
from frappe.permissions import get_user_permissions
from frappe.utils import getdate
from frappe.utils.file_manager import get_content_hash
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from sidra_realestate.api.live_period import period
from sidra_realestate.api.shell import is_staff
from sidra_realestate.services.cashbook import amount, statement_line, statement_rows

BANK_TRANSACTION = "Bank Transaction"
ACCOUNTS = {"is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}
BANK_ACCOUNTS = {"is_company_account": 1, "disabled": 0}
VOUCHER_TYPES = ("payment_entry", "journal_entry", "sales_invoice", "purchase_invoice")
MAX_UPLOAD = 5 * 1024 * 1024
MAX_WORKBOOK_SIZE = 20 * 1024 * 1024
PAGE_SIZE = 100


def _deny():
	frappe.throw(_("You do not have access to this cashbook or record."), frappe.PermissionError)


def can_open():
	return is_staff() and all(frappe.has_permission(dt, "read") for dt in ("Company", "Account", "GL Entry"))


def _company(company):
	if not can_open() or not frappe.get_list("Company", filters={"name": company}, pluck="name", limit=1):
		_deny()


def _cash_accounts(company, **filters):
	return frappe.get_list(
		"Account",
		filters={**ACCOUNTS, "company": company, **filters},
		fields=["name", "account_name", "account_type", "account_currency"],
		order_by="account_name asc, name asc",
		limit=0,
	)


def _currencies(accounts):
	names = {row.account_currency for row in accounts if row.account_currency}
	if not names:
		return set()
	# Select permission is sufficient for Currency links, including for an Auditor.
	return set(frappe.get_list("Currency", filters={"name": ["in", sorted(names)]}, pluck="name", limit=0))


def _bank_accounts(company, **filters):
	if not frappe.has_permission("Bank Account", "read"):
		return []
	return frappe.get_list(
		"Bank Account",
		filters={**BANK_ACCOUNTS, "company": company, **filters},
		fields=["name", "account"],
		limit=0,
	)


@frappe.whitelist(methods=["GET"])
def list_accounts(company: str):
	_company(company)
	accounts = _cash_accounts(company)
	currencies = _currencies(accounts)
	return [row for row in accounts if row.account_currency in currencies]


def _scope(company, account, *, lock=False):
	_company(company)
	accounts = _cash_accounts(company, name=account)
	if not accounts or accounts[0].account_currency not in _currencies(accounts):
		_deny()
	row = accounts[0]
	row.bank_account = None
	if row.account_type == "Bank" and (banks := _bank_accounts(company, account=account)):
		row.bank_account = banks[0].name
	if lock:
		if not row.bank_account or not frappe.db.get_value(
			"Bank Account",
			{"name": row.bank_account, "account": account, "company": company, **BANK_ACCOUNTS},
			"name",
			for_update=True,
		):
			_deny()
	return row


def _allowed_vouchers(keys):
	names_by_type = defaultdict(set)
	for doctype, name in keys:
		if doctype and name:
			names_by_type[doctype].add(name)
	visible = set()
	document_checks = frappe.get_hooks("has_permission")
	user_permissions = get_user_permissions(frappe.session.user)
	for doctype, names in names_by_type.items():
		if not frappe.has_permission(doctype, "read"):
			continue
		names = sorted(names)
		for offset in range(0, len(names), 200):
			readable = frappe.get_list(
				doctype,
				filters={"name": ["in", names[offset : offset + 200]]},
				pluck="name",
				limit=0,
			)
			# List permissions cover parent fields. Document checks also cover child links and hooks.
			if user_permissions or doctype in document_checks or "*" in document_checks:
				readable = [name for name in readable if frappe.has_permission(doctype, "read", doc=name)]
			visible.update((doctype, name) for name in readable)
	return visible


def _as_decimal(value):
	return Decimal(str(value))


def _text(value):
	return format(value, "f")


def _precision(currency):
	return frappe.new_doc(BANK_TRANSACTION, currency=currency).precision("deposit")


def _ledger(company, scope, start, end, offset):
	entries = frappe.get_list(
		"GL Entry",
		filters={"company": company, "account": scope.name, "is_cancelled": 0, "posting_date": ["<=", end]},
		fields=[
			"name",
			"posting_date",
			"voucher_type",
			"voucher_no",
			"account_currency",
			"debit_in_account_currency",
			"credit_in_account_currency",
		],
		order_by="posting_date asc, creation asc, name asc",
		limit=0,
	)
	vouchers = {(row.voucher_type, row.voucher_no) for row in entries}
	# A balance derived from a hidden voucher would also reveal its movement.
	if not vouchers.issubset(_allowed_vouchers(vouchers)):
		_deny()

	opening = receipts = payments = closing = Decimal(0)
	movements = []
	index = 0
	for row in entries:
		if row.account_currency != scope.account_currency:
			frappe.throw(_("A ledger entry has a different account currency. Review the account in Finance."))
		debit, credit = (
			_as_decimal(row.debit_in_account_currency),
			_as_decimal(row.credit_in_account_currency),
		)
		closing += debit - credit
		if row.posting_date < start:
			opening = closing
			continue
		receipts += debit
		payments += credit
		if offset <= index < offset + PAGE_SIZE:
			movements.append(
				{
					"name": row.name,
					"date": str(row.posting_date),
					"voucher_type": row.voucher_type,
					"voucher_no": row.voucher_no,
					"receipt": _text(debit),
					"payment": _text(credit),
					"balance": _text(closing),
				}
			)
		index += 1
	return {
		"opening": _text(opening),
		"receipts": _text(receipts),
		"payments": _text(payments),
		"closing": _text(closing),
		"movements": movements,
		"has_more": index > offset + PAGE_SIZE,
	}


def _statement_summary(scope, start, end, offset):
	if not scope.bank_account or not frappe.has_permission(BANK_TRANSACTION, "read"):
		return None
	filters = {
		"bank_account": scope.bank_account,
		"company": scope.company,
		"currency": scope.account_currency,
		"docstatus": 1,
		"date": ["between", [start, end]],
		"unallocated_amount": [">", 0],
	}
	lines = frappe.get_list(
		BANK_TRANSACTION,
		filters=filters,
		fields=["name", "date", "reference_number", "deposit", "withdrawal", "unallocated_amount"],
		order_by="date asc, name asc",
		start=offset,
		limit=PAGE_SIZE + 1,
	)
	return {
		"lines": lines[:PAGE_SIZE],
		"has_more": len(lines) > PAGE_SIZE,
		"can_add": all(frappe.has_permission(BANK_TRANSACTION, p) for p in ("create", "submit")),
		"can_match": frappe.has_permission(BANK_TRANSACTION, "write"),
	}


@frappe.whitelist(methods=["GET"])
def get_cashbook(
	company: str,
	account: str,
	from_date: str,
	to_date: str,
	observed_balance: str | None = None,
	ledger_offset: int = 0,
	statement_offset: int = 0,
):
	scope = _scope(company, account)
	scope.company = company
	start, end = period(from_date, to_date)
	ledger = _ledger(company, scope, start, end, max(0, ledger_offset))
	precision = _precision(scope.account_currency)
	difference = None
	if observed_balance not in (None, ""):
		try:
			difference = _text(
				round(amount(observed_balance, precision) - _as_decimal(ledger["closing"]), precision)
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
	return {
		**ledger,
		"account_type": scope.account_type,
		"currency": scope.account_currency,
		"precision": precision,
		"difference": difference,
		"statement": _statement_summary(scope, start, end, max(0, statement_offset)),
	}


def _upload(suffixes):
	file = frappe.request.files.get("file")
	filename = PurePath((file.filename or "").replace("\\", "/")).name if file else ""
	if PurePath(filename).suffix.lower() not in suffixes:
		frappe.throw(_("Choose a file of type {0}.").format(", ".join(suffixes)))
	content = file.stream.read(MAX_UPLOAD + 1)
	if not content or len(content) > MAX_UPLOAD:
		frappe.throw(_("Choose a non-empty file of at most 5 MB."))
	return filename, content


def _check_add():
	if not all(frappe.has_permission(BANK_TRANSACTION, p) for p in ("read", "create", "submit")):
		_deny()


def _save_statement_line(company, scope, line):
	# Native statement imports and manual records may already exist. The Bank Account row lock
	# serializes submissions through this screen. A locking read also sees a concurrent commit.
	transaction_id = "sidra-statement-" + sha256(line["reference_number"].casefold().encode()).hexdigest()
	fields = ["name", "date", "currency", "deposit", "withdrawal", "docstatus", "company"]
	existing = frappe.db.get_values(
		BANK_TRANSACTION,
		{"bank_account": scope.bank_account, "transaction_id": transaction_id},
		fields,
		as_dict=True,
		for_update=True,
	) or frappe.db.get_values(
		BANK_TRANSACTION,
		{"bank_account": scope.bank_account, "reference_number": line["reference_number"]},
		fields,
		as_dict=True,
		for_update=True,
	)
	if existing:
		if len(existing) != 1:
			frappe.throw(_("This statement reference already occurs more than once. Review it in Finance."))
		row = existing[0]
		doc = frappe.get_doc(BANK_TRANSACTION, row.name)
		doc.check_permission("read")
		if (
			row.docstatus != 1
			or row.company != company
			or getdate(row.date) != line["date"]
			or row.currency != line["currency"]
			or any(_as_decimal(row[key]) != line[key] for key in ("deposit", "withdrawal"))
		):
			frappe.throw(
				_("Statement reference {0} conflicts with an existing transaction.").format(
					line["reference_number"]
				)
			)
		return doc, False

	doc = frappe.get_doc(
		{
			"doctype": BANK_TRANSACTION,
			"company": company,
			"bank_account": scope.bank_account,
			"transaction_id": transaction_id,
			**line,
		}
	)
	# Native create and submit permissions and validation apply. No voucher is created.
	doc.insert()
	doc.submit()
	return doc, True


def _read_workbook(content, currency, precision):
	with ZipFile(io.BytesIO(content)) as archive:
		if sum(member.file_size for member in archive.infolist()) > MAX_WORKBOOK_SIZE:
			raise ValueError("The expanded workbook is too large.")
	workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
	try:
		return statement_rows(workbook.worksheets[0].values, currency, precision)
	finally:
		workbook.close()


@frappe.whitelist(methods=["POST"])
def import_statement(company: str, account: str):
	_check_add()
	scope = _scope(company, account, lock=True)
	filename, content = _upload((".csv", ".xlsx"))
	precision = _precision(scope.account_currency)
	try:
		if filename.lower().endswith(".csv"):
			rows = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
			lines = statement_rows(rows, scope.account_currency, precision)
		else:
			lines = _read_workbook(content, scope.account_currency, precision)
	except (
		ValueError,
		csv.Error,
		BadZipFile,
		InvalidFileException,
		KeyError,
		OSError,
		IndexError,
		SyntaxError,
	) as exc:
		frappe.throw(
			_("Could not read the statement. {0}").format(str(exc) if isinstance(exc, ValueError) else "")
		)
	created = sum(_save_statement_line(company, scope, line)[1] for line in lines)
	return {"created": created, "duplicates": len(lines) - created}


def _attach_evidence(doc, filename, content):
	doc.check_permission("write")
	if frappe.db.get_value(
		"File",
		{
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"content_hash": get_content_hash(content),
			"is_private": 1,
		},
		"name",
		for_update=True,
	):
		return
	# File applies its native attachment checks and manages private-file transaction callbacks.
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
		}
	).insert()


@frappe.whitelist(methods=["POST"])
def enter_statement_line(
	company: str,
	account: str,
	date: str,
	reference: str,
	deposit: str = "",
	withdrawal: str = "",
	description: str = "",
):
	_check_add()
	scope = _scope(company, account, lock=True)
	filename, content = _upload((".pdf",))
	if not content.startswith(b"%PDF-"):
		frappe.throw(_("Choose the original PDF statement."))
	try:
		line = statement_line(
			date,
			reference,
			scope.account_currency,
			deposit,
			withdrawal,
			description,
			_precision(scope.account_currency),
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	doc, created = _save_statement_line(company, scope, line)
	_attach_evidence(doc, filename, content)
	return {"name": doc.name, "created": created}


def _transaction(company, scope, transaction, *, lock=False):
	if not scope.bank_account or not frappe.has_permission(BANK_TRANSACTION, "read"):
		_deny()
	if not frappe.db.get_value(
		BANK_TRANSACTION,
		{
			"name": transaction,
			"bank_account": scope.bank_account,
			"company": company,
			"currency": scope.account_currency,
			"docstatus": 1,
		},
		"name",
		for_update=lock,
	):
		_deny()
	doc = frappe.get_doc(BANK_TRANSACTION, transaction, for_update=lock)
	doc.check_permission("read")
	return doc


def _candidates(doc, start, end):
	if doc.unallocated_amount <= 0:
		return []
	return [
		row
		for row in reconciliation.get_linked_payments(doc.name, list(VOUCHER_TYPES), start, end)
		if row.paid_amount > 0 and row.currency == doc.currency and start <= getdate(row.posting_date) <= end
	]


@frappe.whitelist(methods=["GET"])
def matching_vouchers(company: str, account: str, transaction: str, from_date: str, to_date: str):
	scope = _scope(company, account)
	doc = _transaction(company, scope, transaction)
	start, end = period(from_date, to_date)
	return [
		{
			"doctype": row.doctype,
			"name": row.name,
			"date": str(row.posting_date),
			"amount": row.paid_amount,
			"reference": row.get("reference_no"),
			"can_match": doc.has_permission("write")
			and frappe.has_permission(row.doctype, "write", doc=row.name),
		}
		for row in _candidates(doc, start, end)
	]


@frappe.whitelist(methods=["POST"])
def match_voucher(
	company: str,
	account: str,
	transaction: str,
	voucher_type: str,
	voucher: str,
	from_date: str,
	to_date: str,
):
	scope = _scope(company, account, lock=True)
	doc = _transaction(company, scope, transaction, lock=True)
	doc.check_permission("write")
	start, end = period(from_date, to_date)
	if voucher_type not in reconciliation.get_doctypes_for_bank_reconciliation() or not _allowed_vouchers(
		{(voucher_type, voucher)}
	):
		_deny()
	target = frappe.get_doc(voucher_type, voucher, for_update=True)
	target.check_permission("read")
	target.check_permission("write")
	if target.company != company or target.docstatus != 1:
		_deny()
	if any(
		row.payment_document == voucher_type and row.payment_entry == voucher for row in doc.payment_entries
	):
		return {"status": doc.status}
	if not any(row.doctype == voucher_type and row.name == voucher for row in _candidates(doc, start, end)):
		frappe.throw(_("This voucher is no longer available to match. Refresh the cashbook."))
	# A concurrent partial allocation may change child rows without changing the voucher itself.
	# Verify that the transaction snapshot used by native matching still has the current allocations.
	allocation_filters = {"payment_document": voucher_type, "payment_entry": voucher, "docstatus": 1}
	allocation_fields = ["name", "allocated_amount"]
	previous = frappe.db.get_values(
		"Bank Transaction Payments", allocation_filters, allocation_fields, order_by="name"
	)
	current = frappe.db.get_values(
		"Bank Transaction Payments",
		allocation_filters,
		allocation_fields,
		order_by="name",
		for_update=True,
	)
	if current != previous:
		frappe.throw(_("This voucher's reconciliation changed. Refresh the cashbook and try again."))
	matched = reconciliation.reconcile_vouchers(
		doc.name,
		frappe.as_json([{"payment_doctype": voucher_type, "payment_name": voucher}]),
	)
	return {"status": matched.status}
