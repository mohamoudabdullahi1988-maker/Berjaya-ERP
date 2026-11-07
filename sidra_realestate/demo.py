"""Synthetic demonstration data for a private staging site (docs/DEPLOYMENT_v0.1.md).

	bench --site <staging> set-config sidra_allow_demo_data 1
	bench --site <staging> execute sidra_realestate.demo.create_demo_data
	bench --site <staging> execute sidra_realestate.demo.export_pdfs --kwargs "{'folder': '/tmp/sidra-pdfs'}"

Refuses to run unless the site sets `sidra_allow_demo_data`, so it cannot touch production by
accident. Every name is synthetic. The one demo clause is marked as a placeholder: it is not
Sidra legal wording (issue #8). Profile A and Profile B are used as they are; Profile B's demo
contract stays a draft. Nothing is posted to the ledger.
"""

import os
from io import BytesIO

import frappe
from frappe.utils import add_days, today

COMPANY = "Sidra Demo Homes"
SCHEME = "DEMO-HAGBAD"
BUYERS = ("Demo Buyer Amina", "Demo Buyer Hodan", "Demo Buyer Warsame")
USERS = {  # role profiles from fixtures/role_profile.json
	"demo.sales@example.com": "Sidra Sales Staff",
	"demo.manager@example.com": "Sidra Sales Management",
	"demo.gm@example.com": "Sidra General Management",
	"demo.pm@example.com": "Sidra Project Staff",
	"demo.finance@example.com": "Sidra Finance Review",
	"demo.outsider@example.com": None,
}
PLACEHOLDER = "[DEMO PLACEHOLDER — not Sidra legal wording; replace with approved text (issue #8)]"


def _guard():
	if not frappe.conf.get("sidra_allow_demo_data"):
		frappe.throw("Demo data is disabled on this site. Set sidra_allow_demo_data only on staging.")


def create_demo_data(company: str | None = None) -> dict:
	"""Create (once) the demo company, people, plots, reservation, contracts and a construction job."""
	_guard()
	company = company or _ensure_company()
	_ensure_customers()
	_ensure_users()
	units = _ensure_units(company)
	summary = {"company": company, "units": units}

	if not frappe.db.exists("Sidra Reservation", {"unit": "DEMO-H-005"}):
		from sidra_realestate.services.reservations import reserve_unit

		summary["reservation"] = reserve_unit("DEMO-H-005", BUYERS[1], days=7)["reservation"]

	summary["hagbad_contract"] = _contract(
		"DEMO-HAGBAD-FULL",
		company,
		BUYERS[0],
		"Profile A",
		[("DEMO-H-001", 5500), ("DEMO-H-002", 5500)],
		"IPN/HL/901/2026",
		submit=True,
	)
	summary["clause_contract"] = _contract(
		"DEMO-CLAUSES",
		company,
		BUYERS[2],
		_demo_profile(),
		[("DEMO-H-003", 5500)],
		"IPN/HL/902/2026",
		submit=True,
	)
	summary["profile_b_draft"] = _contract(
		"DEMO-PROFILE-B", company, BUYERS[1], "Profile B", [("DEMO-H-004", 9000)], "IPN/HL/903/2026", submit=False
	)
	summary["construction_job"] = _construction_job(company)
	frappe.db.commit()
	return summary


def export_pdfs(folder: str) -> list[str]:
	"""Write the demo contracts as PDF (the print format's own generator) to `folder`."""
	_guard()
	os.makedirs(folder, exist_ok=True)
	paths = []
	for marker in ("DEMO-HAGBAD-FULL", "DEMO-CLAUSES", "DEMO-PROFILE-B"):
		name = frappe.db.get_value("Sidra Sale Contract", {"buyer_agent_name": marker}, "name")
		if not name:
			continue
		pdf = frappe.get_print("Sidra Sale Contract", name, print_format="Sidra Sale Contract", as_pdf=True)
		path = os.path.join(folder, f"{name}-{marker}.pdf")
		with open(path, "wb") as fh:
			fh.write(pdf)
		paths.append(path)
	return paths


# ---------------------------------------------------------------- records
def _ensure_company() -> str:
	if frappe.db.exists("Company", COMPANY):
		return COMPANY
	if not frappe.db.exists("Warehouse Type", "Transit"):
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
			if not frappe.db.exists(doctype, record.get("name") or record.get(keys.get(doctype))):
				frappe.get_doc(record).insert(ignore_permissions=True)
		add_uom_data()
	frappe.get_doc(
		{"doctype": "Company", "company_name": COMPANY, "abbr": "SDH", "default_currency": "USD", "country": "Somalia"}
	).insert(ignore_permissions=True)
	return COMPANY


def _ensure_customers():
	group = "Individual" if frappe.db.exists("Customer Group", "Individual") else None
	for name in BUYERS:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Individual",
					"customer_group": group,
					"territory": "All Territories",
				}
			).insert(ignore_permissions=True)


def _ensure_users():
	"""Users without passwords; the administrator sets them with `bench set-password` on staging."""
	for email, profile in USERS.items():
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			if profile and profile not in [row.role_profile for row in user.role_profiles]:
				user.append("role_profiles", {"role_profile": profile})
				user.save(ignore_permissions=True)
			continue
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0].replace(".", " ").title(),
				"send_welcome_email": 0,
				"user_type": "System User",
				"time_zone": "Africa/Mogadishu",
			}
		)
		if profile:
			user.append("role_profiles", {"role_profile": profile})
		user.insert(ignore_permissions=True)


def _ensure_units(company) -> list[str]:
	if not frappe.db.exists("Sidra Scheme", SCHEME):
		frappe.get_doc(
			{
				"doctype": "Sidra Scheme",
				"scheme_code": SCHEME,
				"scheme_name": "Demo Hagbad East",
				"company": company,
				"location": "Demo location",
				"district": "Demo District",
				"neighbourhood": "Demo Neighbourhood",
			}
		).insert(ignore_permissions=True)
	names = []
	for i in range(1, 7):
		code = f"DEMO-H-{i:03d}"
		names.append(code)
		if frappe.db.exists("Sidra Unit", code):
			continue
		frappe.get_doc(
			{
				"doctype": "Sidra Unit",
				"unit_code": code,
				"scheme": SCHEME,
				"unit_type": "Plot",
				"plot_fraction": "Half",
				"dimensions": "9×24 m",
				"district": "Demo District",
				"neighbourhood": "Demo Neighbourhood",
				"land_parcel": "Demo Parcel",
				"boundary_east": "Road",
				"boundary_north": f"DEMO-H-{i + 1:03d}" if i < 6 else "Road",
				"boundary_south": f"DEMO-H-{i - 1:03d}" if i > 1 else "Road",
				"boundary_west": "Open land",
				"cash_price": 9000 if i == 4 else 5500,
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Sidra Unit Price History", {"unit": "DEMO-H-006", "reason": "Demo price review"}):
		entry = frappe.get_doc(
			{
				"doctype": "Sidra Unit Price History",
				"unit": "DEMO-H-006",
				"effective_from": add_days(today(), 30),
				"price": 6000,
				"reason": "Demo price review",
			}
		).insert(ignore_permissions=True)
		entry.submit()
	return names


def _demo_profile() -> str:
	name = "Demo Profile A + placeholder clause"
	if frappe.db.exists("Sidra Contract Profile", name):
		return name
	if not frappe.db.exists("Sidra Contract Clause", "DEMO-PLACEHOLDER"):
		frappe.get_doc(
			{
				"doctype": "Sidra Contract Clause",
				"clause_code": "DEMO-PLACEHOLDER",
				"title": "Demo clause (placeholder)",
				"text_so": PLACEHOLDER,
				"text_en": PLACEHOLDER,
				"approved": 1,
			}
		).insert(ignore_permissions=True)
	values = {
		k: v
		for k, v in frappe.get_doc("Sidra Contract Profile", "Profile A").as_dict().items()
		if k not in ("name", "profile_name", "is_default", "clauses", "creation", "modified", "owner", "modified_by", "idx")
		and not k.startswith("_")
		and k not in ("doctype", "docstatus")
	}
	frappe.get_doc(
		{
			**values,
			"doctype": "Sidra Contract Profile",
			"profile_name": name,
			"is_default": 0,
			"clauses": [{"clause": "DEMO-PLACEHOLDER"}],
		}
	).insert(ignore_permissions=True)
	return name


def _contract(marker, company, customer, profile, units, notary_reference, submit) -> str:
	existing = frappe.db.get_value("Sidra Sale Contract", {"buyer_agent_name": marker}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Sidra Sale Contract",
			"contract_type": "Installment",
			"customer": customer,
			"company": company,
			"signed_on": today(),
			"contract_profile": profile,
			"agreed_price": sum(price for _, price in units),
			"units": [{"unit": unit, "allocated_price": price} for unit, price in units],
			"buyer_agent_name": marker,
			"notary_name": "Demo Notary",
			"notary_reference": notary_reference,
			"parties": [
				{"role": "Seller", "full_name": "Demo Seller Owner", "phone": "+252 63 000 1001"},
				{
					"role": "Seller Guarantor",
					"full_name": "Demo Guarantor",
					"phone": "+252 63 000 1002",
					"id_number": "DEMO-ID-1002",
					"pledged_property": "Demo pledged plot",
				},
				{"role": "Witness", "full_name": "Demo Witness One", "phone": "+252 63 000 1003"},
				{"role": "Witness", "full_name": "Demo Witness Two", "phone": "+252 63 000 1004"},
			],
		}
	).insert(ignore_permissions=True)
	if submit:
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{doc.name}-signed-scan.pdf",
				"content": _placeholder_scan(doc.name),
				"is_private": 1,
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"attached_to_field": "signed_copy",
			}
		).insert(ignore_permissions=True)
		doc.signed_copy = file_doc.file_url
		doc.save(ignore_permissions=True)
		doc.submit()
	return doc.name


def _construction_job(company) -> str:
	existing = frappe.db.get_value("Sidra Construction Job", {"site_location": "Demo site, plot DEMO-H-001"}, "name")
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"customer": BUYERS[0],
				"company": company,
				"service_type": "Full Construction",
				"site_location": "Demo site, plot DEMO-H-001",
				"plot_number": "DEMO-H-001",
				"boq": [
					{"cost_code": "01", "description": "Site clearing (demo)", "qty": 1, "rate": 350},
					{"cost_code": "02", "description": "Excavation (demo)", "qty": 42.5, "rate": 8},
					{"cost_code": "03", "description": "Foundation concrete (demo)", "qty": 18, "rate": 145.5},
				],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _placeholder_scan(name) -> bytes:
	"""A one-page PDF standing in for the signed scan; unique per contract."""
	from pypdf import PdfWriter

	writer = PdfWriter()
	writer.add_blank_page(width=595, height=842)
	writer.add_metadata({"/Title": f"Demo signed scan for {name} (placeholder)"})
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()
