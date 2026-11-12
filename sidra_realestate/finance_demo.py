"""Explicitly opted-in, fictional native accounting data. Never run from hooks or HTTP.

See docs/FINANCE-DEMO_v0.2.md (decision G12). This does not enable Sidra contract posting.

COMPANY is the only place the target Company is named; the adapter, reporting and tests import it.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import frappe

from sidra_realestate.services.executive_metrics import decimal_amount, money

COMPANY = "Sidra Homes"
# "SHD" identities, so the v0.1 "SFD" records on a site that ran the old loader are left alone.
CUSTOMER = "SHD Fictional Buyer"
SUPPLIER = "SHD Fictional Supplier"
ITEM = "SHD Fictional Service"
PRICE_LIST = "SHD Fictional USD"
SCHEME = "SHD-FICTIONAL"
ACCOUNT_PREFIX = "Fictional Demo "
MANIFEST = "sidra-finance-demo-v1.json"
FLAGS = ("sidra_allow_demo_data", "sidra_finance_demo_site", "sidra_allow_finance_demo_vouchers")
VOUCHERS = {"Sales Invoice": 3, "Purchase Invoice": 2, "Payment Entry": 4, "Journal Entry": 1}
EXPECTED = {
	"Bank": "123000.00",
	"Receivables": "35000.00",
	"Payables": "-8000.00",
	"Capital": "-100000.00",
	"Revenue": "-70000.00",
	"Expenses": "20000.00",
}


def enabled(company):
	return company == COMPANY and all(frappe.conf.get(flag) in (1, True, "1") for flag in FLAGS)


def _guard():
	if not enabled(COMPANY):
		frappe.throw("Finance demo requires all three staging-only flags; see FINANCE-DEMO_v0.2.md.")
	if frappe.session.user != "Administrator":
		frappe.throw(
			"Run the finance demo using Administrator through bench execute.", frappe.PermissionError
		)


def _manifest(required=True):
	"""The private ownership registry. Any doubt about it is a refusal, never "proceed"."""
	try:
		files = frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Company",
				"attached_to_name": COMPANY,
				"file_name": MANIFEST,
				"is_private": 1,
			},
			pluck="name",
		)
		if not files and not required:
			return None
		if len(files) != 1:
			raise ValueError("missing or ambiguous")
		data = json.loads(frappe.get_doc("File", files[0]).get_content())
		if data.get("schema") != 2 or data.get("company") != COMPANY:
			raise ValueError("not for this Company")
		for doctype in VOUCHERS:
			if not all(isinstance(name, str) for name in data["vouchers"][doctype]):
				raise ValueError("voucher registry")
	except Exception as exc:
		frappe.throw(
			f"Refusing: the finance demo ownership manifest of Company '{COMPANY}' is missing, ambiguous "
			f"or unreadable ({type(exc).__name__}). No data was changed."
		)
	return data


def _refuse_foreign_gl(data):
	"""Decision G12: never post into, or vouch for, a Company with ledger rows we do not own.

	`data` is the manifest, or None on a first run, when any GL row at all is foreign.
	"""
	owned = (
		{(doctype, name) for doctype, names in data["vouchers"].items() for name in names} if data else set()
	)
	rows = frappe.get_all(
		"GL Entry",
		filters={"company": COMPANY, "is_cancelled": 0},
		fields=["voucher_type", "voucher_no"],
		order_by="creation asc",
		limit_page_length=0,
	)
	foreign = [
		(row.voucher_type, row.voucher_no) for row in rows if (row.voucher_type, row.voucher_no) not in owned
	]
	if foreign:
		first = ", ".join(f"{doctype} {name}" for doctype, name in list(dict.fromkeys(foreign))[:3])
		frappe.throw(
			f"Refusing: Company '{COMPANY}' has {len(foreign)} GL entries not owned by the finance demo "
			f"manifest (first: {first}). The finance demo will not post into a Company with foreign "
			"ledger activity."
		)


def report_links(data):
	base = {"company": COMPANY, "from_date": data["from_date"], "to_date": data["as_of"]}
	financial = {
		"company": COMPANY,
		"filter_based_on": "Date Range",
		"period_start_date": data["from_date"],
		"period_end_date": data["as_of"],
		"periodicity": "Yearly",
	}
	filters = {
		"General Ledger": base,
		"Trial Balance": {
			**base,
			"from_date": max(data["from_date"], data["as_of"][:4] + "-01-01"),
			"fiscal_year": data["fiscal_years"][-1],
		},
		"Profit and Loss Statement": financial,
		"Balance Sheet": financial,
		"Accounts Receivable": {"company": COMPANY, "report_date": data["as_of"]},
		"Accounts Payable": {"company": COMPANY, "report_date": data["as_of"]},
	}
	return {
		name: "/app/query-report/" + quote(name) + "?" + urlencode(values) for name, values in filters.items()
	}


def create_finance_demo_data():
	"""Create once and commit ten submitted vouchers in the existing Company named by COMPANY.

	Reruns verify the existing dataset and return its original dates; never add or repair entries.
	All setup/posting is one transaction. No caller-controlled Company or amounts.
	The Company itself is never created, renamed or edited.
	"""
	_guard()
	if not frappe.db.exists("Company", COMPANY):
		frappe.throw(f"Refusing: Company '{COMPANY}' does not exist. The finance demo never creates it.")
	# First read of the run, before any insert: the only protection of this Company's books.
	data = _manifest(required=False)
	_refuse_foreign_gl(data)
	if data:
		verify_finance_demo(data)
		return {**data, "reports": report_links(data), "created": False}
	for doctype, filters in (
		("Customer", {"customer_name": CUSTOMER}),
		("Supplier", {"supplier_name": SUPPLIER}),
		("Item", {"item_code": ITEM}),
		("Price List", {"price_list_name": PRICE_LIST}),
		("Sidra Scheme", {"scheme_code": SCHEME}),
		("Account", {"company": COMPANY, "account_name": ("like", ACCOUNT_PREFIX + "%")}),
	):
		if frappe.db.exists(doctype, filters):
			frappe.throw(f"Reserved demo identity already exists: {doctype}. No data was changed.")
	for doctype in VOUCHERS:
		# A draft or cancelled voucher has no live GL row, but it is still not ours.
		if frappe.db.exists(doctype, {"company": COMPANY}):
			frappe.throw(f"Refusing: Company '{COMPANY}' already has {doctype} records. No data was changed.")
	try:
		data = _create()
		verify_finance_demo(data)
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": MANIFEST,
				"content": json.dumps(data, indent=2),
				"is_private": 1,
				"attached_to_doctype": "Company",
				"attached_to_name": COMPANY,
			}
		).insert()
	except Exception:
		# This manual entrypoint owns its transaction, including private File rollback callbacks.
		frappe.db.rollback()
		frappe.cache.delete_value("fiscal_years")  # ERPNext may have cached a rolled-back year
		raise
	frappe.db.commit()
	return {**data, "reports": report_links(data), "created": True}


def _fiscal_year(day):
	"""Use the Company's own Fiscal Year for `day`; add a Company-only one if it has none."""
	for name in frappe.get_all(
		"Fiscal Year",
		filters={"disabled": 0, "year_start_date": ("<=", day), "year_end_date": (">=", day)},
		order_by="year_start_date asc",
		pluck="name",
	):
		companies = frappe.get_all("Fiscal Year Company", filters={"parent": name}, pluck="company")
		if not companies or COMPANY in companies:
			return name, False
	name = f"SHD Fictional FY {day.year}"
	if frappe.db.exists("Fiscal Year", name):
		frappe.throw("Reserved demo Fiscal Year already exists; refusing to adopt it.")
	# ERPNext refuses this if it overlaps a Fiscal Year that also applies to the Company.
	_insert(
		"Fiscal Year",
		year=name,
		year_start_date=date(day.year, 1, 1),
		year_end_date=date(day.year, 12, 31),
		companies=[{"company": COMPANY}],
	)
	return name, True


def _insert(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert()


def _create():
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from sidra_realestate.demo import _ensure_presets

	_ensure_presets()
	# Match the staff report's business day even when the site's timezone differs.
	today = datetime.now(ZoneInfo("Africa/Mogadishu")).date()
	start = today - timedelta(days=45)
	company = frappe.db.get_value(
		"Company", COMPANY, ["abbr", "default_currency", "cost_center"], as_dict=True
	)
	if company.default_currency != "USD" or not company.cost_center:
		frappe.throw(
			f"Refusing: Company '{COMPANY}' needs USD and a default cost center. No data was changed."
		)
	years, created_years = [], []
	for day in (start, today):
		name, created = _fiscal_year(day)
		if name not in years:
			years.append(name)
			if created:
				created_years.append(name)
	accounts, groups = {}, {}
	for label, root_type, account_type in (
		("Bank", "Asset", "Bank"),
		("Receivables", "Asset", "Receivable"),
		("Payables", "Liability", "Payable"),
		("Capital", "Equity", ""),
		("Revenue", "Income", "Income Account"),
		("Expenses", "Expense", "Expense Account"),
	):
		if root_type not in groups:
			roots = frappe.get_all(
				"Account",
				filters={
					"company": COMPANY,
					"root_type": root_type,
					"is_group": 1,
					"parent_account": ("is", "not set"),
				},
				pluck="name",
			)
			if len(roots) != 1:
				frappe.throw(f"Refusing: Company '{COMPANY}' has no single {root_type} root account.")
			# A clearly marked parent per root, so the demo never sits among the Company's own accounts.
			groups[root_type] = _insert(
				"Account",
				account_name=f"{ACCOUNT_PREFIX}Accounts ({root_type})",
				company=COMPANY,
				parent_account=roots[0],
				account_currency="USD",
				is_group=1,
			).name
		accounts[label] = _insert(
			"Account",
			account_name=ACCOUNT_PREFIX + label,
			company=COMPANY,
			parent_account=groups[root_type],
			account_type=account_type,
			account_currency="USD",
			is_group=0,
		).name
	# The Company's own default accounts are left as they are; every voucher names its accounts.
	customer = _insert(
		"Customer",
		customer_name=CUSTOMER,
		customer_type="Individual",
		customer_group="Individual",
		territory="All Territories",
		default_currency="USD",
		accounts=[{"company": COMPANY, "account": accounts["Receivables"]}],
	).name
	supplier = _insert(
		"Supplier",
		supplier_name=SUPPLIER,
		supplier_group="All Supplier Groups",
		supplier_type="Company",
		default_currency="USD",
		accounts=[{"company": COMPANY, "account": accounts["Payables"]}],
	).name
	item = _insert(
		"Item",
		item_code=ITEM,
		item_name=ITEM,
		item_group="Services",
		stock_uom="Nos",
		is_stock_item=0,
		item_defaults=[
			{
				"company": COMPANY,
				"income_account": accounts["Revenue"],
				"expense_account": accounts["Expenses"],
			}
		],
	).name
	_insert("Price List", price_list_name=PRICE_LIST, currency="USD", enabled=1, buying=1, selling=1)
	vouchers = {doctype: [] for doctype in VOUCHERS}
	capital = _insert(
		"Journal Entry",
		company=COMPANY,
		voucher_type="Journal Entry",
		posting_date=start,
		user_remark="FICTIONAL DEMO ONLY: owner capital, no opening balances imported.",
		accounts=[
			{"account": accounts["Bank"], "debit_in_account_currency": 100000},
			{"account": accounts["Capital"], "credit_in_account_currency": 100000},
		],
	).submit()
	vouchers["Journal Entry"].append(capital.name)
	for doctype, amount, offset, due_offset, paid in (
		("Sales Invoice", 40000, -45, -15, 25000),
		("Sales Invoice", 10000, -20, -5, 10000),
		("Sales Invoice", 20000, -8, 15, 0),
		("Purchase Invoice", 18000, -12, -2, 10000),
		("Purchase Invoice", 2000, -5, 10, 2000),
	):
		is_sale = doctype == "Sales Invoice"
		invoice = _insert(
			doctype,
			company=COMPANY,
			**({"customer": customer} if is_sale else {"supplier": supplier}),
			currency="USD",
			conversion_rate=1,
			**({"selling_price_list": PRICE_LIST} if is_sale else {"buying_price_list": PRICE_LIST}),
			price_list_currency="USD",
			plc_conversion_rate=1,
			ignore_pricing_rule=1,
			posting_date=today + timedelta(days=offset),
			set_posting_time=1,
			due_date=today + timedelta(days=due_offset),
			**({"debit_to": accounts["Receivables"]} if is_sale else {"credit_to": accounts["Payables"]}),
			remarks="FICTIONAL DEMO ONLY: non-stock service; no tax, deposits, fees, FX or title transfer.",
			items=[
				{
					"item_code": item,
					"qty": 1,
					"rate": amount,
					"cost_center": company.cost_center,
					"income_account": accounts["Revenue"],
					"expense_account": accounts["Expenses"],
				}
			],
		).submit()
		vouchers[doctype].append(invoice.name)
		if paid:
			payment = get_payment_entry(doctype, invoice.name, bank_account=accounts["Bank"])
			payment.paid_amount = payment.received_amount = paid
			payment.references[0].allocated_amount = paid
			payment.posting_date = payment.reference_date = today
			payment.reference_no = "FICTIONAL-DEMO-" + invoice.name
			payment.remarks = "FICTIONAL DEMO ONLY: allocated native invoice payment."
			payment.insert().submit()
			vouchers["Payment Entry"].append(payment.name)
	operational = _operational(customer, today)
	return {
		"schema": 2,
		"company": COMPANY,
		"currency": "USD",
		"as_of": str(today),
		"from_date": str(start),
		"fiscal_years": years,
		"created_fiscal_years": created_years,
		"accounts": accounts,
		"account_groups": groups,
		"vouchers": vouchers,
		"expected_net_debits": EXPECTED,
		"operational": operational,
		"notice": "Fictional sample vouchers on a marked test site (decision G12). Not real Sidra transactions.",
	}


def _operational(customer, today):
	"""Reuse existing contract capture and stage records; no contract-to-ledger mapping.

	Three new fictional plots in their own scheme: the Company's existing units are never touched.
	"""
	scheme = _insert("Sidra Scheme", scheme_code=SCHEME, scheme_name="Fictional Demo Plots", company=COMPANY)
	units = []
	for index, price in enumerate((30000, 11000, 11000), start=1):
		units.append(
			_insert(
				"Sidra Unit",
				unit_code=f"{SCHEME}-{index}",
				scheme=scheme.name,
				unit_type="Plot",
				cash_price=price,
			).name
		)
	contract = _insert(
		"Sidra Sale Contract",
		company=COMPANY,
		customer=customer,
		source="External (registered)",
		external_reference="SHD-FICTIONAL-EXTERNAL-001",
		contract_type="Installment",
		signed_on=today,
		agreed_price=30000,
		units=[{"unit": units[0], "allocated_price": 30000}],
		schedule=[
			{"row_type": "Installment", "due_date": today + timedelta(days=offset), "amount": 10000}
			for offset in (5, 35, 65)
		],
	)
	attachment = _insert(
		"File",
		file_name="fictional-external-original.txt",
		is_private=1,
		attached_to_doctype=contract.doctype,
		attached_to_name=contract.name,
		attached_to_field="signed_copy",
		content="FICTIONAL DEMO ORIGINAL - not a real or legally signed agreement.\n"
		f"Reference SHD-FICTIONAL-EXTERNAL-001; buyer {customer}; seller Fictional Demo Seller.\n"
		f"Unit {units[0]}; USD 30,000; three USD 10,000 installments, due "
		+ ", ".join(str(today + timedelta(days=offset)) for offset in (5, 35, 65))
		+ ". No deposit, fee, tax or interest. This commercial example is independent of the service invoices.\n",
	)
	contract.signed_copy = attachment.file_url
	contract.save().submit()
	job = _insert(
		"Sidra Construction Job",
		company=COMPANY,
		customer=customer,
		service_type="Design Only",
		site_location="Fictional demo site - not an actual project",
		status="In Progress",
		stages=[
			{
				"stage_name": "Fictional design milestone",
				"planned_end": today - timedelta(days=3),
				"completion_pct": 40,
				"status": "In Progress",
			}
		],
	)
	leads = [
		_insert("Lead", first_name="Fictional Demo", last_name=f"Prospect {index}", company=COMPANY).name
		for index in (1, 2)
	]
	return {
		"units": units,
		"contract": contract.name,
		"attachment": attachment.name,
		"job": job.name,
		"leads": leads,
	}


def verify_finance_demo(data=None):
	"""Read-only native-voucher and GL checks; refuse to repair an altered demo."""
	_guard()
	data = data or _manifest()
	_refuse_foreign_gl(data)
	for doctype, count in VOUCHERS.items():
		rows = frappe.get_all(doctype, filters={"company": COMPANY}, fields=["name", "docstatus"])
		if (
			len(rows) != count
			or {r.name for r in rows} != set(data["vouchers"][doctype])
			or any(r.docstatus != 1 for r in rows)
		):
			frappe.throw(f"Finance demo {doctype} records changed; refusing to overwrite or duplicate them.")
	balances = {account: Decimal(0) for account in data["accounts"].values()}
	debit = credit = Decimal(0)
	for entry in frappe.get_all(
		"GL Entry",
		filters={"company": COMPANY, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
		limit_page_length=0,
	):
		if entry.account not in balances:
			frappe.throw("Unexpected demo GL account; no records were changed.")
		d, c = decimal_amount(entry.debit), decimal_amount(entry.credit)
		debit += d
		credit += c
		balances[entry.account] += d - c
	if debit != credit or money(debit) != "237000.00":
		frappe.throw("Finance demo GL does not match the expected balanced postings.")
	for label, expected in EXPECTED.items():
		if money(balances[data["accounts"][label]]) != expected:
			frappe.throw(f"Finance demo {label} balance changed; no records were changed.")
	return {"debits": money(debit), "credits": money(credit), "net_debits": EXPECTED}
