# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G40: Sidra sales also appear in ERPNext Selling, as records only.

- An issued Sidra Sale Quotation creates a submitted ERPNext **Quotation**.
- A confirmed Sidra Sale Contract creates a submitted ERPNext **Sales Order**.
- Cancelling the Sidra record cancels its ERPNext copy.

The Sidra records stay the sale: units, contract profile, schedule, approvals and title rules live
there. The ERPNext copies carry one line per unit with a sale-type item ("Land plot sale",
"House sale", "Apartment sale"), the unit on the line, and a link back. Prices are copied, never
worked out here:
- Quotation: the unit's listed price as the price-list rate; the rate is the installment price when
  the quotation offers an installment plan (it has a contract profile), else the cash price.
- Sales Order: each unit's allocated price from the confirmed contract; the order's total is the
  contract's agreed price.
No invoice, payment or ledger entry is created (Quotations and Sales Orders post nothing). Invoices
and payments follow the existing finance flow and gates.

A copy that cannot be made never blocks the Sidra record: the attempt is rolled back to a savepoint,
logged, and noted as a comment on the Sidra record; `sync_selling` can make it later. Staff cannot
cancel or change a copy by hand: it follows its Sidra record.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import flt, getdate

QUOTATION = "Sidra Sale Quotation"
CONTRACT = "Sidra Sale Contract"
ITEM_GROUP = "Real Estate Sales"
SALE_ITEMS = {"Plot": "Land plot sale", "House": "House sale", "Apartment": "Apartment sale"}
SYNCING = "sidra_selling_sync"

CUSTOM_FIELDS = {
	"Quotation": [
		{
			"fieldname": "sidra_sale_quotation",
			"label": "Sidra Sale Quotation",
			"fieldtype": "Link",
			"options": QUOTATION,
			"insert_after": "party_name",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
		}
	],
	"Sales Order": [
		{
			"fieldname": "sidra_sale_contract",
			"label": "Sidra Sale Contract",
			"fieldtype": "Link",
			"options": CONTRACT,
			"insert_after": "customer",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
		}
	],
	"Quotation Item": [
		{
			"fieldname": "sidra_unit",
			"label": "Unit",
			"fieldtype": "Link",
			"options": "Sidra Unit",
			"insert_after": "item_name",
			"read_only": 1,
			"in_list_view": 1,
		}
	],
	"Sales Order Item": [
		{
			"fieldname": "sidra_unit",
			"label": "Unit",
			"fieldtype": "Link",
			"options": "Sidra Unit",
			"insert_after": "item_name",
			"read_only": 1,
			"in_list_view": 1,
		}
	],
}


def ensure_selling_setup():
	"""Custom fields, the item group and the sale-type items (after_install / after_migrate)."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)
	if not frappe.db.exists("Item Group", "All Item Groups"):
		return  # ERPNext's setup wizard has not run yet; the next migrate finishes this
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": ITEM_GROUP, "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)
	uom = "Nos" if frappe.db.exists("UOM", "Nos") else None
	for name in SALE_ITEMS.values():
		if frappe.db.exists("Item", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": name,
				"item_name": name,
				"item_group": ITEM_GROUP,
				"stock_uom": uom,
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 0,
				"include_item_in_manufacturing": 0,
				"description": f"{name} (Berjaya). The unit is on each line.",
			}
		).insert(ignore_permissions=True)


def price_list(currency):
	"""An empty selling price list per currency, so no ERPNext price changes the copied rates.

	Made as the system on first use. ERPNext makes a new selling price list the site's default when
	none is set; this one is only for the copies, so that default is left as it was."""
	name = f"{ITEM_GROUP} {currency}"
	if frappe.db.exists("Price List", name):
		return name
	default = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	with _as_system():
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": name,
				"currency": currency,
				"selling": 1,
				"buying": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	if not default and frappe.db.get_single_value("Selling Settings", "selling_price_list") == name:
		frappe.db.set_single_value("Selling Settings", "selling_price_list", default)
	return name


# ---------------------------------------------------------------------- events (hooks.py)


def quotation_submitted(doc, method=None):
	_safely(doc, lambda: make_quotation(doc))


def contract_submitted(doc, method=None):
	_safely(doc, lambda: make_sales_order(doc))


def quotation_cancelled(doc, method=None):
	_safely(doc, lambda: _cancel("Quotation", {"sidra_sale_quotation": doc.name}))


def contract_cancelled(doc, method=None):
	_safely(doc, lambda: _cancel("Sales Order", {"sidra_sale_contract": doc.name}))


def protect_copy(doc, method=None):
	"""A copy follows its Sidra record: no cancelling or changing it by hand."""
	link = doc.get("sidra_sale_quotation") or doc.get("sidra_sale_contract")
	if link and not frappe.flags.get(SYNCING):
		frappe.throw(
			_("{0} follows {1}. Change or cancel {1} instead.").format(doc.name, link),
			frappe.PermissionError,
		)


# ---------------------------------------------------------------------- making the copies


def make_quotation(sidra):
	if frappe.db.exists("Quotation", {"sidra_sale_quotation": sidra.name, "docstatus": ["<", 2]}):
		return None
	installment = bool(sidra.contract_profile)
	items = []
	for row in sidra.units:
		rate = flt(row.installment_price if installment else row.cash_price, 2)
		items.append(_line(row.unit, rate, price_list_rate=flt(row.listed_price, 2)))
	doc = frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": sidra.customer,
			"company": sidra.company,
			"currency": sidra.currency,
			"transaction_date": sidra.quotation_date,
			"valid_till": sidra.valid_until,
			"order_type": "Sales",
			"ignore_pricing_rule": 1,
			"sidra_sale_quotation": sidra.name,
			"terms": _("Copy of {0} ({1} offer). The Sidra quotation is the offer.").format(
				sidra.name, _("installment") if installment else _("cash")
			),
			"items": items,
		}
	)
	return _submit(doc, sidra)


def make_sales_order(sidra):
	if frappe.db.exists("Sales Order", {"sidra_sale_contract": sidra.name, "docstatus": ["<", 2]}):
		return None
	allocated = flt(sum(flt(row.allocated_price, 2) for row in sidra.units), 2)
	if allocated != flt(sidra.agreed_price, 2):
		frappe.throw(
			_("Unit prices add up to {0}, not the agreed price {1}; no Sales Order was made").format(
				allocated, flt(sidra.agreed_price, 2)
			)
		)
	date = getdate(sidra.signed_on)
	doc = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": sidra.customer,
			"company": sidra.company,
			"currency": sidra.currency,
			"transaction_date": date,
			"delivery_date": date,
			"order_type": "Sales",
			"ignore_pricing_rule": 1,
			"sidra_sale_contract": sidra.name,
			"terms": _("Copy of {0}. The Sidra contract is the agreement.").format(sidra.name),
			"items": [_line(row.unit, flt(row.allocated_price, 2), date=date) for row in sidra.units],
		}
	)
	return _submit(doc, sidra)


def _line(unit, rate, price_list_rate=None, date=None):
	values = frappe.db.get_value(
		"Sidra Unit", unit, ["unit_type", "unit_code", "scheme", "block"], as_dict=True
	)
	item = SALE_ITEMS.get(values.unit_type)
	if not item:
		frappe.throw(_("Unit {0} has no unit type").format(unit))
	if not frappe.db.exists("Item", item):
		# A site migrated before ERPNext's setup finished has no sale items yet: make them now.
		with _as_system():
			ensure_selling_setup()
	line = {
		"item_code": item,
		"qty": 1,
		"rate": rate,
		"sidra_unit": unit,
		"description": " · ".join(str(v) for v in (values.scheme, values.block, values.unit_code) if v),
	}
	if date:
		line["delivery_date"] = date
	if price_list_rate:
		line["price_list_rate"] = price_list_rate
	return line


def _submit(doc, sidra):
	"""Insert and submit the copy as the system: it is made because an authorised user issued or
	confirmed the Sidra record, and ERPNext would otherwise also check that user's rights on Items
	and Price Lists, which Sidra sales roles do not hold. The comment names who triggered it."""
	doc.flags.ignore_permissions = True
	by = frappe.session.user
	with _as_system():
		doc.selling_price_list = price_list(doc.currency)
		doc.price_list_currency = doc.currency
		doc.plc_conversion_rate = 1
		frappe.flags["sidra_selling_copy"] = True  # G44: only copies of Sidra records are made
		try:
			doc.insert()
		finally:
			frappe.flags["sidra_selling_copy"] = False
		doc.submit()
	sidra.add_comment(
		"Info", _("ERPNext {0} {1} created as a copy (triggered by {2})").format(_(doc.doctype), doc.name, by)
	)
	return doc.name


@contextmanager
def _as_system():
	previous = frappe.session.user
	if previous == "Administrator":
		yield
		return
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(previous)


def _cancel(doctype, filters):
	for name in frappe.get_all(doctype, filters={**filters, "docstatus": 1}, pluck="name"):
		frappe.flags[SYNCING] = True
		try:
			copy = frappe.get_doc(doctype, name)
			copy.flags.ignore_permissions = True
			with _as_system():
				copy.cancel()
		finally:
			frappe.flags[SYNCING] = False


def _safely(sidra, action):
	"""Make the copy; on any failure undo only the copy, log it and note it on the Sidra record."""
	savepoint = "sidra_selling"
	frappe.db.savepoint(savepoint)
	try:
		action()
	except Exception as exc:
		frappe.db.rollback(save_point=savepoint)
		frappe.clear_messages()
		frappe.log_error(title=f"ERPNext Selling copy of {sidra.doctype} {sidra.name}")
		sidra.add_comment(
			"Info", _("ERPNext Selling copy not made: {0}. Use Sync to try again.").format(str(exc)[:300])
		)


def backfill_selling(company=None):
	"""Make the missing copies of every submitted Sidra quotation and contract (System Manager).

	For adopting G40 on a site that already has sales. Idempotent: a record that has its copy is
	skipped. Run once after deploying:
		bench --site <site> execute sidra_realestate.services.erpnext_selling.backfill_selling
	"""
	frappe.only_for("System Manager")
	filters = {"docstatus": 1, **({"company": company} if company else {})}
	made, failed = {}, {}
	sources = (
		(QUOTATION, "sidra_sale_quotation", "Quotation", {"status": "Issued"}),
		(CONTRACT, "sidra_sale_contract", "Sales Order", {}),
	)
	for doctype, link, copy, extra in sources:
		for name in frappe.get_all(
			doctype, filters={**filters, **extra}, pluck="name", order_by="creation asc"
		):
			if frappe.db.exists(copy, {link: name, "docstatus": ["<", 2]}):
				continue
			sidra = frappe.get_doc(doctype, name)
			frappe.db.savepoint("sidra_backfill")
			try:
				made[name] = make_quotation(sidra) if doctype == QUOTATION else make_sales_order(sidra)
			except Exception as exc:
				frappe.db.rollback(save_point="sidra_backfill")
				frappe.clear_messages()
				failed[name] = str(exc)[:300]
	frappe.db.commit()
	result = {"made": made, "failed": failed}
	print(result)
	return result


@frappe.whitelist(methods=["POST"])
def sync_selling(doctype: str, name: str):
	"""Make a missing copy of a submitted Sidra quotation or contract (Sales Managers, GM)."""
	if doctype not in (QUOTATION, CONTRACT):
		frappe.throw(_("Only Sidra quotations and contracts have ERPNext Selling copies"))
	sidra = frappe.get_doc(doctype, name)
	sidra.check_permission("submit")
	if sidra.docstatus != 1:
		frappe.throw(_("{0} is not submitted").format(name))
	made = make_quotation(sidra) if doctype == QUOTATION else make_sales_order(sidra)
	return {"created": made}
