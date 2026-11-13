"""Explicitly opted-in, fictional pilot demonstration dataset. Never run from hooks or HTTP.

See docs/PILOT-DEMO_v0.1.md (decision G15). This widens the fictional voucher set of the finance
demo so a client demonstration has twelve months of movement in every module; it does not enable
Sidra contract posting, refunds, penalties or title transfer.

	bench --site <staging> set-config sidra_allow_demo_data 1
	bench --site <staging> set-config sidra_finance_demo_site 1
	bench --site <staging> set-config sidra_allow_finance_demo_vouchers 1
	bench --site <staging> execute sidra_realestate.pilot_demo.create_pilot_demo_data

Guards are those of the finance demo and are not relaxed: Administrator only, all three staging
flags, a private ownership manifest, a refusal to touch a Company holding ledger rows the
manifests do not own, one transaction with full rollback, and a rerun that changes nothing.
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe

from sidra_realestate.finance_demo import COMPANY, FLAGS
from sidra_realestate.finance_demo import MANIFEST as FINANCE_MANIFEST
from sidra_realestate.services.pilot_dataset import PREFIX, build, totals

MANIFEST = "sidra-pilot-demo-v1.json"
SCHEMA = 1
CUSTOMER_PREFIX = PREFIX + " "
SUPPLIER = f"{PREFIX} Pilot Supplier"
ITEM = f"{PREFIX} Pilot Service"
PRICE_LIST = f"{PREFIX} Pilot USD"
ACCOUNT_PREFIX = "Pilot Demo "
PROFILE = f"{PREFIX} Pilot Installment Profile"
VOUCHER_TYPES = ("Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry")
NOTICE = (
	"FICTIONAL PILOT DEMONSTRATION DATA (decision G15). Not real Sidra transactions, customers, "
	"contracts or land."
)


# ---------------------------------------------------------------- guards
def _guard():
	if not all(frappe.conf.get(flag) in (1, True, "1") for flag in FLAGS):
		frappe.throw("Pilot demo requires all three staging-only flags; see docs/PILOT-DEMO_v0.1.md.")
	if frappe.session.user != "Administrator":
		frappe.throw("Run the pilot demo using Administrator through bench execute.", frappe.PermissionError)


def _read_manifest(file_name, schema, required=True):
	"""A private ownership registry attached to the Company. Any doubt is a refusal."""
	try:
		files = frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Company",
				"attached_to_name": COMPANY,
				"file_name": file_name,
				"is_private": 1,
			},
			pluck="name",
		)
		if not files and not required:
			return None
		if len(files) != 1:
			raise ValueError("missing or ambiguous")
		data = json.loads(frappe.get_doc("File", files[0]).get_content())
		if data.get("company") != COMPANY:
			raise ValueError("not for this Company")
		if schema is not None and data.get("schema") != schema:
			raise ValueError("unexpected schema")
		for doctype in VOUCHER_TYPES:
			if not all(isinstance(name, str) for name in data.get("vouchers", {}).get(doctype, [])):
				raise ValueError("voucher registry")
	except Exception as exc:
		frappe.throw(
			f"Refusing: the ownership manifest '{file_name}' of Company '{COMPANY}' is missing, "
			f"ambiguous or unreadable ({type(exc).__name__}). No data was changed."
		)
	return data


def owned_vouchers():
	"""Every voucher either manifest claims. Read by this loader and by the finance demo guard."""
	owned = set()
	for file_name, schema in ((FINANCE_MANIFEST, None), (MANIFEST, None)):
		data = _read_manifest(file_name, schema, required=False)
		if not data:
			continue
		for doctype, names in data.get("vouchers", {}).items():
			owned.update((doctype, name) for name in names)
	return owned


def _refuse_foreign_gl():
	"""Decision G14, unchanged: never post into a Company holding ledger rows we do not own.

	Runs before the first insert, inside this run's transaction. Fails closed.
	"""
	owned = owned_vouchers()
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
			f"Refusing: Company '{COMPANY}' has {len(foreign)} GL entries not owned by a demo "
			f"ownership manifest (first: {first}). The pilot demo will not post into a Company "
			"with foreign ledger activity."
		)


# ---------------------------------------------------------------- entry point
def create_pilot_demo_data():
	"""Create once and commit the twelve-month pilot dataset in the Company named by COMPANY.

	A rerun verifies the manifest and returns it; it never adds, repairs or repositions anything.
	The Company itself is never created, renamed or edited.
	"""
	_guard()
	if not frappe.db.exists("Company", COMPANY):
		frappe.throw(f"Refusing: Company '{COMPANY}' does not exist. The pilot demo never creates it.")
	existing = _read_manifest(MANIFEST, SCHEMA, required=False)
	# First database read of the run, before any insert.
	_refuse_foreign_gl()
	if existing:
		return {**existing, "created": False}
	for doctype, filters in (
		("Supplier", {"supplier_name": SUPPLIER}),
		("Item", {"item_code": ITEM}),
		("Price List", {"price_list_name": PRICE_LIST}),
		("Sidra Contract Profile", {"profile_name": PROFILE}),
		("Sidra Scheme", {"scheme_code": ("like", PREFIX + "-%")}),
		("Account", {"company": COMPANY, "account_name": ("like", ACCOUNT_PREFIX + "%")}),
	):
		if frappe.db.exists(doctype, filters):
			frappe.throw(f"Reserved pilot identity already exists: {doctype}. No data was changed.")
	try:
		data = _create()
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": MANIFEST,
				"content": json.dumps(data, indent=2, default=str),
				"is_private": 1,
				"attached_to_doctype": "Company",
				"attached_to_name": COMPANY,
			}
		).insert()
	except Exception:
		# This manual entrypoint owns its transaction, including private File rollback callbacks.
		frappe.db.rollback()
		frappe.cache.delete_value("fiscal_years")
		raise
	frappe.db.commit()
	return {**data, "created": True}


def _insert(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _create():
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from sidra_realestate.demo import _ensure_presets, _placeholder_scan
	from sidra_realestate.finance_demo import _fiscal_year

	_ensure_presets()
	today = datetime.now(ZoneInfo("Africa/Mogadishu")).date()
	plan = build(today)
	company = frappe.db.get_value(
		"Company", COMPANY, ["abbr", "default_currency", "cost_center"], as_dict=True
	)
	if company.default_currency != "USD" or not company.cost_center:
		frappe.throw(
			f"Refusing: Company '{COMPANY}' needs USD and a default cost center. No data was changed."
		)

	years, created_years = [], []
	for day in {plan.from_date, today}:
		name, created = _fiscal_year(day)
		if name not in years:
			years.append(name)
			if created:
				created_years.append(name)

	accounts = _accounts()
	customers = _customers(plan, accounts)
	supplier = _supplier(accounts)
	item = _item(accounts)
	schemes, units = _property(plan)
	profile = _profile()
	sales = _sales(plan, profile, _placeholder_scan)
	jobs = _construction(plan)
	vouchers = _finance(plan, accounts, customers, supplier, item, company, get_payment_entry)

	return {
		"schema": SCHEMA,
		"company": COMPANY,
		"currency": "USD",
		"as_of": str(today),
		"from_date": str(plan.from_date),
		"fiscal_years": years,
		"created_fiscal_years": created_years,
		"accounts": accounts,
		"vouchers": vouchers,
		"counts": {**plan.counts(), "schemes_created": len(schemes), "units_created": len(units)},
		"expected_totals": {k: str(v) for k, v in totals(plan).items()},
		"sales": sales,
		"jobs": jobs,
		"notice": NOTICE,
	}


# ---------------------------------------------------------------- masters
def _accounts():
	"""Clearly marked demo parents per root, so pilot rows never sit among the Company's own."""
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
	return accounts


def _customers(plan, accounts):
	"""Fictional buyers with KYC; four in forty stay unverified so the contract gate is visible."""
	from frappe.utils import now_datetime

	names = []
	for entry in plan.customers:
		name = CUSTOMER_PREFIX + entry["name"]
		customer = _insert(
			"Customer",
			customer_name=name,
			customer_type="Individual",
			customer_group="Individual",
			territory="All Territories",
			default_currency="USD",
			accounts=[{"company": COMPANY, "account": accounts["Receivables"]}],
		).name
		kyc = _insert(
			"Sidra Customer KYC",
			customer=customer,
			id_type=entry["id_type"],
			id_number=entry["id_number"],
			phone=entry["phone"],
			address=entry["address"],
		)
		if entry["verified"]:
			from sidra_realestate.demo import _placeholder_scan

			kyc.id_document = _insert(
				"File",
				file_name=f"pilot-id-{entry['id_number']}.pdf",
				content=_placeholder_scan(entry["id_number"]),
				is_private=1,
				attached_to_doctype=kyc.doctype,
				attached_to_name=kyc.name,
				attached_to_field="id_document",
			).file_url
			kyc.status = "Verified"
			kyc.verified_by = frappe.session.user
			kyc.verified_on = now_datetime()
			kyc.flags.verifying = True
			kyc.save(ignore_permissions=True)
		names.append(customer)
	return names


def _supplier(accounts):
	return _insert(
		"Supplier",
		supplier_name=SUPPLIER,
		supplier_group="All Supplier Groups",
		supplier_type="Company",
		default_currency="USD",
		accounts=[{"company": COMPANY, "account": accounts["Payables"]}],
	).name


def _item(accounts):
	name = _insert(
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
	return name


def _profile():
	"""A pilot profile copied from Profile A, so quotations and contracts have terms to freeze."""
	source = frappe.get_doc("Sidra Contract Profile", "Profile A").as_dict()
	skip = {
		"name",
		"profile_name",
		"is_default",
		"clauses",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"idx",
		"doctype",
		"docstatus",
	}
	values = {k: v for k, v in source.items() if k not in skip and not k.startswith("_")}
	# Overrides go into the dict: Profile A already carries `installments`, so passing it
	# alongside **values is a duplicate keyword argument.
	values.update(profile_name=PROFILE, is_default=0, installments=24)
	return _insert("Sidra Contract Profile", **values).name


# ---------------------------------------------------------------- property
def _property(plan):
	schemes = [
		_insert(
			"Sidra Scheme",
			scheme_code=entry["scheme_code"],
			scheme_name=entry["scheme_name"],
			company=COMPANY,
			location=f"{entry['district']} pilot location",
			district=entry["district"],
			neighbourhood=entry["neighbourhood"],
		).name
		for entry in plan.schemes
	]
	units = []
	for entry in plan.units:
		units.append(
			_insert(
				"Sidra Unit",
				unit_code=entry["unit_code"],
				scheme=entry["scheme"],
				company=COMPANY,
				unit_type=entry["unit_type"],
				district=entry["district"],
				neighbourhood=entry["neighbourhood"],
				plot_fraction=entry["plot_fraction"],
				dimensions=entry["dimensions"],
				area_sqm=entry["area_sqm"],
				land_parcel=entry["land_parcel"],
				bedrooms=entry["bedrooms"],
				floors=entry["floors"],
				offplan_status=entry["offplan_status"],
				boundary_east="Road",
				boundary_north="Pilot neighbour plot",
				boundary_south="Pilot neighbour plot",
				boundary_west="Open land",
				cash_price=entry["cash_price"],
			).name
		)
	for entry in plan.price_history:
		_insert(
			"Sidra Unit Price History",
			unit=entry["unit"],
			effective_from=entry["effective_from"],
			price=entry["price"],
			reason=entry["reason"],
		).submit()
	return schemes, units


# ---------------------------------------------------------------- sales
def _sales(plan, profile, placeholder_scan):
	created = {"quotations": [], "reservations": [], "contracts": [], "titles": []}
	for entry in plan.quotations:
		doc = _insert(
			"Sidra Sale Quotation",
			customer=CUSTOMER_PREFIX + entry["customer"],
			company=COMPANY,
			quotation_date=entry["quotation_date"],
			valid_until=entry["valid_until"],
			contract_profile=profile,
			installments=entry["installments"],
			notes=NOTICE,
			units=[
				{
					"unit": entry["unit"],
					"listed_price": entry["listed_price"],
					"cash_price": entry["cash_price"],
					"installment_price": entry["installment_price"],
				}
			],
		)
		created["quotations"].append(doc.name)

	# A Sidra Reservation refuses to be written directly: it is created and closed by the
	# Reserve Unit service, which also moves the unit's status. The loader uses that service
	# rather than setting its bypass flag, so the demo data follows the same path as a user.
	from sidra_realestate.services.reservations import _close, reserve_unit

	for entry in plan.reservations:
		name = reserve_unit(entry["unit"], CUSTOMER_PREFIX + entry["customer"], days=entry["days"])[
			"reservation"
		]
		if entry["status"] != "Active":
			_close(name, entry["status"])
		created["reservations"].append(name)

	by_reference = {}
	for entry in plan.contracts:
		values = {
			"contract_type": entry["contract_type"],
			"source": entry["source"],
			"customer": CUSTOMER_PREFIX + entry["customer"],
			"company": COMPANY,
			"signed_on": entry["signed_on"],
			"agreed_price": entry["agreed_price"],
			"units": entry["units"],
			"buyer_agent_name": entry["reference"],
			"notary_name": "Pilot Notary",
			"notary_reference": entry["notary_reference"],
			# The signing gate (SAL-19) needs exactly one Seller, a Seller Guarantor with a
			# pledged property, and two Witnesses with phone numbers.
			"parties": [
				{"role": "Seller", "full_name": "Pilot Seller Owner", "phone": "+252 63 000 4001"},
				{
					"role": "Seller Guarantor",
					"full_name": "Pilot Guarantor",
					"phone": "+252 63 000 4002",
					"id_number": f"{PREFIX}-ID-4002",
					"pledged_property": "Pilot pledged plot",
				},
				{"role": "Witness", "full_name": "Pilot Witness One", "phone": "+252 63 000 4003"},
				{"role": "Witness", "full_name": "Pilot Witness Two", "phone": "+252 63 000 4004"},
			],
		}
		# A cash contract carries no profile, no source and no external reference: the
		# controller refuses one that does. Only the generated installment path takes a profile.
		if entry["contract_type"] == "Installment":
			if entry["external_reference"]:
				values["external_reference"] = entry["external_reference"]
			else:
				values["contract_profile"] = profile
		else:
			values.pop("source", None)
		if entry["contract_type"] == "Installment":
			values.update(
				down_payment=entry["down_payment"],
				installments=entry["installments"],
				due_day=entry["due_day"],
				schedule=[
					{"due_date": row["due_date"], "amount": row["amount"]} for row in entry["schedule"]
				],
			)
		doc = _insert("Sidra Sale Contract", **values)
		if entry["submit"]:
			doc.signed_copy = _insert(
				"File",
				file_name=f"{doc.name}-pilot-signed.pdf",
				content=placeholder_scan(doc.name),
				is_private=1,
				attached_to_doctype=doc.doctype,
				attached_to_name=doc.name,
				attached_to_field="signed_copy",
			).file_url
			doc.save(ignore_permissions=True)
			doc.submit()
		by_reference[entry["reference"]] = doc.name
		created["contracts"].append(doc.name)

	for entry in plan.titles:
		contract = by_reference.get(entry["contract"])
		if not contract:
			continue
		doc = _insert(
			"Sidra Title Transfer",
			contract=contract,
			unit=entry["unit"],
			company=COMPANY,
			land_office_reference=entry["land_office_reference"],
			deed_number=entry["deed_number"],
			documents=[{"document": name, "received": 1} for name in entry["documents"]],
		)
		created["titles"].append(doc.name)
	return created


# ---------------------------------------------------------------- construction
def _construction(plan):
	"""Jobs with BOQ, stages and billing percentages; quotations and variations stay drafts.

	Nothing here is invoiced or posted: construction remains recorded only (G11).
	"""
	created = {"jobs": [], "quotations": [], "variations": [], "inspections": []}
	for entry in plan.jobs:
		job = _insert(
			"Sidra Construction Job",
			customer=CUSTOMER_PREFIX + entry["customer"],
			company=COMPANY,
			service_type=entry["service_type"],
			site_location=entry["site_location"],
			plot_number=entry["plot_number"],
			boq=entry["boq"],
			stages=[
				{
					"stage_name": stage["stage_name"],
					"status": stage["status"],
					"planned_start": stage["planned_start"],
					"planned_end": stage["planned_end"],
					"completion_pct": stage["completion_pct"],
					"billing_pct": stage["billing_pct"],
				}
				for stage in entry["stages"]
			],
		)
		created["jobs"].append(job.name)
		if entry["quotation"]:
			quotation = _insert(
				"Sidra Construction Quotation",
				job=job.name,
				company=COMPANY,
				pricing_basis="BOQ",
				valid_until=plan.as_of + timedelta(days=30),
				scope=f"{NOTICE} Pilot scope for {entry['reference']}.",
				boq=entry["boq"],
				start_date=entry["started_on"],
				duration_days=entry["duration_days"],
				retention_pct=entry["retention_pct"],
				retention_period_months=entry["retention_period_months"],
			)
			created["quotations"].append(quotation.name)
		if entry["variation"]:
			variation = _insert(
				"Sidra Variation Order",
				job=job.name,
				company=COMPANY,
				amount=entry["variation"],
				description=f"{NOTICE} Pilot additional works for {entry['reference']}.",
			)
			created["variations"].append(variation.name)
	return created


# ---------------------------------------------------------------- finance
def _finance(plan, accounts, customers, supplier, item, company, get_payment_entry):
	"""Fictional service revenue and running costs over twelve months, plus opening capital.

	Every voucher created here is recorded in the manifest, so the no-foreign-GL guard
	recognises it on a rerun and refuses anything it does not own.
	"""
	vouchers = {doctype: [] for doctype in VOUCHER_TYPES}
	figures = totals(plan)
	capital = _insert(
		"Journal Entry",
		company=COMPANY,
		voucher_type="Journal Entry",
		posting_date=plan.from_date,
		user_remark=f"{NOTICE} Owner capital; no opening balances imported.",
		accounts=[
			{"account": accounts["Bank"], "debit_in_account_currency": figures["capital"]},
			{"account": accounts["Capital"], "credit_in_account_currency": figures["capital"]},
		],
	).submit()
	vouchers["Journal Entry"].append(capital.name)

	for index, entry in enumerate(plan.invoices):
		is_sale = entry["kind"] == "Sales Invoice"
		party = {"customer": customers[index % len(customers)]} if is_sale else {"supplier": supplier}
		invoice = _insert(
			entry["kind"],
			company=COMPANY,
			**party,
			currency="USD",
			conversion_rate=1,
			**({"selling_price_list": PRICE_LIST} if is_sale else {"buying_price_list": PRICE_LIST}),
			price_list_currency="USD",
			plc_conversion_rate=1,
			ignore_pricing_rule=1,
			posting_date=entry["posting_date"],
			set_posting_time=1,
			due_date=entry["due_date"],
			**({"debit_to": accounts["Receivables"]} if is_sale else {"credit_to": accounts["Payables"]}),
			remarks=f"{NOTICE} Non-stock service; no tax, deposits, fees, FX or title transfer.",
			items=[
				{
					"item_code": item,
					"qty": 1,
					"rate": entry["amount"],
					"cost_center": company.cost_center,
					"income_account": accounts["Revenue"],
					"expense_account": accounts["Expenses"],
				}
			],
		).submit()
		vouchers[entry["kind"]].append(invoice.name)
		if entry["paid"]:
			payment = get_payment_entry(entry["kind"], invoice.name, bank_account=accounts["Bank"])
			payment.paid_amount = payment.received_amount = entry["paid"]
			payment.references[0].allocated_amount = entry["paid"]
			payment.posting_date = payment.reference_date = entry["posting_date"]
			payment.reference_no = f"{PREFIX}-PAY-{invoice.name}"
			payment.remarks = f"{NOTICE} Allocated native invoice payment."
			payment.insert(ignore_permissions=True).submit()
			vouchers["Payment Entry"].append(payment.name)
	return vouchers


def verify_pilot_demo():
	"""Read-only check that the posted ledger still matches the manifest. Changes nothing."""
	_guard()
	data = _read_manifest(MANIFEST, SCHEMA)
	_refuse_foreign_gl()
	posted = {
		doctype: frappe.db.count(doctype, {"company": COMPANY, "docstatus": 1}) for doctype in VOUCHER_TYPES
	}
	expected = {doctype: len(names) for doctype, names in data["vouchers"].items()}
	return {"company": COMPANY, "expected": expected, "posted": posted, "counts": data["counts"]}
