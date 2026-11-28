"""Read-only count of the records behind each ERPNext Desk module (docs/DESK-DATA-AUDIT_v0.1.md).

Changes nothing. Run on a site to see which Desk modules hold data for a Company:

	bench --site <site> execute sidra_realestate.desk_audit.count_records --kwargs "{'company': 'Sidra Homes'}"
"""

import frappe

# Desk module -> the record types staff open there. Sidra's own records are listed under the module
# they belong to, so an empty ERPNext list can be read next to where the data actually is.
MODULES = {
	"Selling (ERPNext)": ["Quotation", "Sales Order", "Delivery Note"],
	"Real Estate Sales (Sidra)": [
		"Sidra Sale Quotation",
		"Sidra Reservation",
		"Sidra Sale Contract",
		"Sidra Title Transfer",
	],
	"Properties (Sidra)": ["Sidra Scheme", "Sidra Unit"],
	"CRM": ["Lead", "Opportunity", "Customer", "Sidra Customer KYC"],
	"Accounting": ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "GL Entry"],
	"Buying": ["Supplier", "Purchase Order", "Purchase Receipt"],
	"Stock": ["Item", "Warehouse", "Stock Entry"],
	"Assets": ["Asset", "Asset Category"],
	"Projects": ["Project", "Task", "Timesheet"],
	"Construction (Sidra)": [
		"Sidra Construction Job",
		"Sidra Construction Quotation",
		"Sidra BOQ Revision",
		"Sidra Variation Order",
		"Sidra Inspection Report",
		"Sidra Project Risk",
	],
}


def count_records(company=None):
	frappe.only_for("System Manager")
	result = {}
	for module, doctypes in MODULES.items():
		counts = {}
		for doctype in doctypes:
			if not frappe.db.exists("DocType", doctype):
				counts[doctype] = "not installed"
				continue
			filters = {}
			if company and frappe.get_meta(doctype).has_field("company"):
				filters["company"] = company
			counts[doctype] = frappe.db.count(doctype, filters)
		result[module] = counts
	for module, counts in result.items():
		print(module)
		for doctype, count in counts.items():
			print(f"  {doctype:32} {count}")
	return result


# Native ERPNext records staff are meant to open in Desk (G40-G42, G37), checked per person.
VISIBILITY = (
	"Quotation",
	"Sales Order",
	"Item",
	"Project",
	"Task",
	"Asset",
	"Asset Category",
	"Warehouse",
	"Material Request",
)
RIGHTS = ("read", "write", "create")


def role_visibility(users=None):
	"""What each Sidra staff user can do with the native records, by their actual roles (read only).

	Changes nothing. Without `users`, checks every enabled System User holding a Sidra role:
		bench --site <site> execute sidra_realestate.desk_audit.role_visibility
	"""
	frappe.only_for("System Manager")
	if not users:
		users = sorted(
			{
				row.parent
				for row in frappe.get_all(
					"Has Role",
					filters={"role": ["like", "Sidra %"], "parenttype": "User"},
					fields=["parent"],
				)
				if frappe.db.get_value("User", row.parent, ["enabled", "user_type"]) == (1, "System User")
			}
		)
	result = {}
	for user in users:
		rights = {}
		for doctype in VISIBILITY:
			if not frappe.db.exists("DocType", doctype):
				rights[doctype] = "not installed"
				continue
			allowed = [r for r in RIGHTS if frappe.has_permission(doctype, r, user=user)]
			rights[doctype] = "/".join(allowed) or "-"
		result[user] = rights
	width = max([len(d) for d in VISIBILITY] + [8])
	for user, rights in result.items():
		print(user, "·", ", ".join(r for r in frappe.get_roles(user) if r.startswith("Sidra ")))
		for doctype, value in rights.items():
			print(f"  {doctype:{width}} {value}")
	return result
