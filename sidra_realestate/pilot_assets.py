"""Fictional company assets for the test site's Assets module (decision G40, 25 Nov 2026).

On top of the pilot dataset (`pilot_demo.py`, G16), this loader once adds clearly marked demo
accounts for fixed assets and depreciation under the pilot's own demo account groups, sets up the
asset categories with them (`services/assets.setup_asset_categories`) and records eight fictional
existing assets (two per category) at two locations. Assets are submitted as existing assets with a
straight-line schedule; that posts nothing, and no depreciation entry can be posted until Finance
approves (G40). The guards are the pilot's: Administrator only, the three staging flags, the pilot's
manifest must exist, one transaction with full rollback, a private manifest of its own, and a rerun
that changes nothing.

	bench --site <staging> execute sidra_realestate.pilot_assets.create_pilot_assets
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import add_days, add_months

from sidra_realestate.finance_demo import COMPANY
from sidra_realestate.pilot_demo import ACCOUNT_PREFIX, _guard, _read_manifest
from sidra_realestate.pilot_demo import MANIFEST as PILOT_MANIFEST
from sidra_realestate.pilot_demo import SCHEMA as PILOT_SCHEMA
from sidra_realestate.services.assets import CATEGORIES, setup_asset_categories

MANIFEST = "sidra-pilot-assets-v1.json"
SCHEMA = 1
LOCATIONS = ("Demo head office, Hargeisa", "Demo site yard, Masalaha")

# (name, category, purchase amount, months ago, location index)
ASSETS = (
	("Demo pickup truck", "Vehicles", 28000, 20, 1),
	("Demo site van", "Vehicles", 24000, 9, 1),
	("Demo concrete mixer", "Plant and equipment", 18000, 15, 1),
	("Demo mini excavator", "Plant and equipment", 45000, 6, 1),
	("Demo office furniture set", "Office equipment", 3500, 22, 0),
	("Demo printer and copier", "Office equipment", 2200, 11, 0),
	("Demo laptops (5)", "IT equipment", 4500, 14, 0),
	("Demo network and server", "IT equipment", 3800, 4, 0),
)


def create_pilot_assets():
	"""Create once and commit; a rerun returns the manifest and changes nothing."""
	_guard()
	if not _read_manifest(PILOT_MANIFEST, PILOT_SCHEMA, required=False):
		frappe.throw("Refusing: load the pilot dataset first (pilot_demo.create_pilot_demo_data).")
	existing = _read_manifest(MANIFEST, SCHEMA, required=False)
	if existing:
		return {**existing, "created": False}
	gl_before = frappe.db.count("GL Entry", {"company": COMPANY})
	try:
		data = _create()
		if frappe.db.count("GL Entry", {"company": COMPANY}) != gl_before:
			frappe.throw("Refusing: recording the demo assets would post to the ledger. Nothing was kept.")
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
		frappe.db.rollback()
		raise
	frappe.db.commit()
	return {**data, "created": True}


def _create():
	today = datetime.now(ZoneInfo("Africa/Mogadishu")).date()
	accounts = _accounts()
	setup_asset_categories(COMPANY, *accounts)
	locations = [_location(name) for name in LOCATIONS]
	cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
	assets = []
	for name, category, amount, months_ago, where in ASSETS:
		purchased = add_months(today, -months_ago)
		years = CATEGORIES[category]
		doc = frappe.get_doc(
			{
				"doctype": "Asset",
				"asset_name": name,
				"item_code": category,
				"asset_category": category,
				"company": COMPANY,
				"location": locations[where],
				"cost_center": cost_center,
				"asset_type": "Existing Asset",
				"purchase_date": purchased,
				"available_for_use_date": purchased,
				"net_purchase_amount": amount,
				"purchase_amount": amount,
				"calculate_depreciation": 1,
				"finance_books": [
					{
						"depreciation_method": "Straight Line",
						"total_number_of_depreciations": years,
						"frequency_of_depreciation": 12,
						"depreciation_start_date": add_days(add_months(purchased, 12), -1),
					}
				],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		assets.append(doc.name)
	return {
		"schema": SCHEMA,
		"company": COMPANY,
		"as_of": str(today),
		"accounts": list(accounts),
		"locations": locations,
		"assets": assets,
	}


def _accounts():
	"""Demo ledger accounts under the pilot's own demo groups, never among the Company's."""
	made = []
	for label, root_type, account_type in (
		("Fixed assets", "Asset", "Fixed Asset"),
		("Accumulated depreciation", "Asset", "Accumulated Depreciation"),
		("Depreciation", "Expense", "Depreciation"),
	):
		group = frappe.db.get_value(
			"Account",
			{"company": COMPANY, "account_name": f"{ACCOUNT_PREFIX}Accounts ({root_type})", "is_group": 1},
			"name",
		)
		if not group:
			frappe.throw(f"Refusing: the pilot's demo {root_type} account group is missing.")
		made.append(
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": ACCOUNT_PREFIX + label,
					"company": COMPANY,
					"parent_account": group,
					"account_type": account_type,
					"account_currency": "USD",
					"is_group": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	return made


def _location(name):
	if not frappe.db.exists("Location", name):
		frappe.get_doc({"doctype": "Location", "location_name": name}).insert(ignore_permissions=True)
	return name
