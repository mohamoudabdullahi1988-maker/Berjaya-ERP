"""Shared test records for the Sidra integration tests. Synthetic names only (rule 8).

Records are created idempotently and committed, so concurrency tests on a second DB
connection can see them. Everything carries a `_Test` prefix.
"""

import itertools
import random
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
PROJECT_MANAGER = "sidra.pm@example.com"
OTHER_PROJECT_MANAGER = "sidra.pm2@example.com"
INSPECTOR = "sidra.inspector@example.com"


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
	ensure_user(PROJECT_MANAGER, ["Sidra Project Manager", "Projects User"])
	ensure_user(OTHER_PROJECT_MANAGER, ["Sidra Project Manager", "Projects User"])
	ensure_user(INSPECTOR, ["Sidra Inspector", "Projects User"])
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


_notary_counter = itertools.count(random.randrange(1000, 90000))


def _blank_pdf() -> bytes:
	"""A valid one-page blank PDF with unique metadata (Frappe de-duplicates identical files)."""
	from io import BytesIO

	from pypdf import PdfWriter

	writer = PdfWriter()
	writer.add_blank_page(width=595, height=842)
	writer.add_metadata({"/Title": f"_Test signed scan {frappe.generate_hash(length=12)}"})
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


def private_file(name="signed-contract.pdf", attached_to=None, is_private=1, field="signed_copy", content=None):
	"""A File as uploaded through a form; attached to `attached_to`'s `field` (Signed Copy) if given."""
	values = {
		"doctype": "File",
		"file_name": f"{frappe.generate_hash(length=8)}-{name}",
		"content": content or _blank_pdf(),
		"is_private": is_private,
	}
	if attached_to is not None:
		values.update(
			attached_to_doctype=attached_to.doctype,
			attached_to_name=attached_to.name,
			attached_to_field=field,
		)
	return frappe.get_doc(values).insert(ignore_permissions=True).file_url


_PNG_1PX = (
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def site_photo(is_private=1):
	"""A 1-pixel PNG with unique trailing bytes (Frappe de-duplicates identical files)."""
	import base64

	content = base64.b64decode(_PNG_1PX) + frappe.generate_hash(length=16).encode()
	return private_file(name="site-photo.png", is_private=is_private, content=content)


def attach_signed_copy(contract, **file_values):
	"""Upload a signed scan to the saved contract's Signed Copy field and save, as staff do."""
	contract.signed_copy = private_file(attached_to=contract, **file_values)
	contract.save()
	return contract


def signing_values():
	"""Notary and parties a contract needs before submit (SAL-19). Synthetic names.

	The signed copy is attached separately with `attach_signed_copy`, once the contract has a name.
	"""
	n = next(_notary_counter)
	return {
		# The signing gate below is the Generated path's; registered (External) contracts are
		# tested in test_sidra_contract_capture.py. Cash contracts ignore `source`.
		"source": "Generated from profile",
		"notary_name": "_Test Notary",
		"notary_reference": f"IPN/HL/{n % 1000:03d}/{2000 + n // 1000}",
		"parties": [
			{"role": "Seller", "full_name": "_Test Seller Owner", "phone": "+252 63 000 0001"},
			{
				"role": "Seller Guarantor",
				"full_name": "_Test Guarantor",
				"phone": "+252 63 000 0002",
				"id_number": "TEST-0002",
				"pledged_property": "_Test pledged plot 1",
			},
			{"role": "Witness", "full_name": "_Test Witness One", "phone": "+252 63 000 0003"},
			{"role": "Witness", "full_name": "_Test Witness Two", "phone": "+252 63 000 0004"},
		],
	}


def make_held_profile():
	"""A copy of Profile B that is on legal hold, to test the hold mechanism.

	Profile B itself has no hold since decision D4 (issue #13); the mechanism stays (SRS v2.0 §3.3).
	"""
	doc = frappe.copy_doc(frappe.get_doc("Sidra Contract Profile", "Profile B"))
	doc.profile_name = unique("_Test Held Profile")
	doc.is_default = 0
	doc.legal_hold = 1
	doc.legal_hold_reason = "_Test legal hold"
	return doc.insert(ignore_permissions=True)


def make_job(**values):
	"""A construction job for the test Company and buyer (Full Construction, template stages)."""
	return frappe.get_doc(
		{
			"doctype": "Sidra Construction Job",
			"customer": BUYER,
			"company": COMPANY,
			"service_type": "Full Construction",
			**values,
		}
	).insert(ignore_permissions=True)
