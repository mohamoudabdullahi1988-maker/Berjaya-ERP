"""Shared test records for the Sidra integration tests. Synthetic names only (rule 8).

Records are created idempotently and committed, so concurrency tests on a second DB
connection can see them. Everything carries a `_Test` prefix.
"""

from contextlib import contextmanager

import frappe

COMPANY = "_Test Sidra Homes"
OTHER_COMPANY = "_Test Sidra Other"
BUYER = "_Test Buyer Amina"
OTHER_BUYER = "_Test Buyer Hodan"
SALES_USER = "sidra.sales@example.com"
SALES_MANAGER = "sidra.manager@example.com"
GENERAL_MANAGER = "sidra.gm@example.com"
SYSTEM_ONLY = "sidra.sysadmin@example.com"
OUTSIDER = "sidra.outsider@example.com"


def ensure_base_records():
	ensure_erpnext_presets()
	ensure_company(COMPANY, "_TSH")
	ensure_company(OTHER_COMPANY, "_TSO")
	ensure_customer(BUYER)
	ensure_customer(OTHER_BUYER)
	ensure_user(SALES_USER, ["Sidra Sales User"])
	ensure_user(SALES_MANAGER, ["Sidra Sales Manager"])
	ensure_user(GENERAL_MANAGER, ["Sidra General Manager"])
	ensure_user(SYSTEM_ONLY, ["System Manager"])
	ensure_user(OUTSIDER, [])
	frappe.db.commit()


def ensure_erpnext_presets():
	"""ERPNext preset records (warehouse types, groups, territories) that a Company needs.

	Mirrors erpnext.tests.utils.BootStrapTestData.make_presets without its India master data.
	"""
	if frappe.db.exists("Warehouse Type", "Transit"):
		return
	from erpnext.setup.setup_wizard.operations.install_fixtures import add_uom_data, get_preset_records

	keys = {
		"Address Template": "country",
		"Item Group": "item_group_name",
		"Territory": "territory_name",
		"Customer Group": "customer_group_name",
		"Supplier Group": "supplier_group_name",
		"Sales Person": "sales_person_name",
		"Mode of Payment": "mode_of_payment",
		"Activity Type": "activity_type",
		"Item Attribute": "attribute_name",
		"Party Type": "party_type",
		"Project Type": "project_type",
		"Print Heading": "print_heading",
		"Share Type": "title",
		"Market Segment": "market_segment",
		"Workstation Operating Component": "component_name",
	}
	for record in get_preset_records("Somalia"):
		doctype = record.get("doctype")
		name = record.get("name") or record.get(keys.get(doctype))
		if not frappe.db.exists(doctype, name):
			frappe.get_doc(record).insert(ignore_permissions=True)
	add_uom_data()
	frappe.db.commit()


def ensure_company(name, abbr):
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": abbr,
				"default_currency": "USD",
				"country": "Somalia",
			}
		).insert(ignore_permissions=True)
	return name


def ensure_customer(name):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Individual",
				"customer_group": "Individual",
				"territory": "All Territories",
			}
		).insert(ignore_permissions=True)
	return name


def ensure_user(email, roles):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


def make_scheme(code, company=COMPANY):
	if not frappe.db.exists("Sidra Scheme", code):
		frappe.get_doc(
			{"doctype": "Sidra Scheme", "scheme_code": code, "scheme_name": f"{code} scheme", "company": company}
		).insert(ignore_permissions=True)
	return code


def make_unit(code, scheme, **values):
	doc = frappe.get_doc(
		{
			"doctype": "Sidra Unit",
			"unit_code": code,
			"scheme": scheme,
			"unit_type": "Plot",
			"plot_fraction": "Half",
			"dimensions": "9×24 m",
			"district": "M/Haybe",
			"neighbourhood": "Masalaha",
			**values,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def unique(prefix):
	return f"{prefix}-{frappe.generate_hash(length=6).upper()}"


@contextmanager
def as_user(user):
	previous = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(previous)
