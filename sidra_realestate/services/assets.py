# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G41: Sidra's own assets in ERPNext Assets, straight-line, nothing posted yet.

- Four asset categories with **straight-line** depreciation at the proposed useful lives (yearly):
  Vehicles 5 years, Plant and equipment 8, Office equipment 5, IT equipment 3. Each has a
  fixed-asset item of the same name, so an Asset can be recorded against it.
- The accounts are Finance's choice: `setup_asset_categories` takes them for one Company. Nothing
  is invented; a category gets an account row only for a Company Finance named.
- **No depreciation entry is posted until Finance approves** the method, lives and accounts:
  a Journal Entry of type *Depreciation Entry* is refused before submit, and automatic
  depreciation booking is kept off, until the site config holds `sidra_depreciation_approved: 1`.
  Recording and submitting an existing asset posts nothing (ERPNext books no ledger entry for an
  existing asset without a purchase document).
Plots and houses for sale stay Sidra Units, not assets.
"""

import frappe
from frappe import _

# category -> useful life in years (proposed; Finance approves before any posting)
CATEGORIES = {
	"Vehicles": 5,
	"Plant and equipment": 8,
	"Office equipment": 5,
	"IT equipment": 3,
}
ITEM_GROUP = "Fixed Assets"
APPROVED = "sidra_depreciation_approved"


def depreciation_approved():
	return frappe.conf.get(APPROVED) in (1, True, "1")


def keep_depreciation_off():
	"""after_install / after_migrate: no automatic depreciation booking before Finance approves."""
	if depreciation_approved() or not frappe.db.exists("DocType", "Accounts Settings"):
		return
	if frappe.db.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically"):
		frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 0)


def refuse_depreciation_entry(doc, method=None):
	"""before_submit on Journal Entry."""
	if doc.voucher_type == "Depreciation Entry" and not depreciation_approved():
		frappe.throw(
			_(
				"Depreciation is not posted until Finance approves the method, useful lives and "
				"accounts (decision G41)"
			),
			title=_("Depreciation not approved yet"),
		)


def setup_asset_categories(
	company, fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
):
	"""Create the categories and their items, with Finance's accounts for `company` (System Manager).

	Idempotent: an existing category keeps its depreciation settings and gains an account row only
	for a Company it does not have yet.
		bench --site <site> execute sidra_realestate.services.assets.setup_asset_categories \\
			--kwargs "{'company': ..., 'fixed_asset_account': ..., ...}"
	"""
	frappe.only_for("System Manager")
	accounts = {
		"fixed_asset_account": (fixed_asset_account, "Fixed Asset"),
		"accumulated_depreciation_account": (accumulated_depreciation_account, "Accumulated Depreciation"),
		"depreciation_expense_account": (depreciation_expense_account, "Depreciation"),
	}
	for field, (account, account_type) in accounts.items():
		values = frappe.db.get_value(
			"Account", account, ["company", "account_type", "is_group"], as_dict=True
		)
		if not values or values.company != company or values.is_group:
			frappe.throw(_("{0} is not a ledger account of {1}").format(account, company))
		if values.account_type != account_type:
			frappe.throw(_("{0} must have account type {1}").format(account, account_type))
	_ensure_item_group()
	made = []
	for category, years in CATEGORIES.items():
		row = {"company_name": company, **{field: account for field, (account, _type) in accounts.items()}}
		if frappe.db.exists("Asset Category", category):
			doc = frappe.get_doc("Asset Category", category)
			if not any(r.company_name == company for r in doc.accounts):
				doc.append("accounts", row)
				doc.flags.ignore_permissions = True
				doc.save()
		else:
			frappe.get_doc(
				{
					"doctype": "Asset Category",
					"asset_category_name": category,
					"finance_books": [
						{
							"depreciation_method": "Straight Line",
							"total_number_of_depreciations": years,
							"frequency_of_depreciation": 12,
						}
					],
					"accounts": [row],
				}
			).insert(ignore_permissions=True)
			made.append(category)
		_ensure_item(category)
	return {"categories": list(CATEGORIES), "created": made}


def _ensure_item_group():
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": ITEM_GROUP, "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)


def _ensure_item(category):
	if frappe.db.exists("Item", category):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": category,
			"item_name": category,
			"item_group": ITEM_GROUP,
			"stock_uom": "Nos" if frappe.db.exists("UOM", "Nos") else None,
			"is_stock_item": 0,
			"is_fixed_asset": 1,
			"asset_category": category,
			"is_sales_item": 0,
			"include_item_in_manufacturing": 0,
		}
	).insert(ignore_permissions=True)
