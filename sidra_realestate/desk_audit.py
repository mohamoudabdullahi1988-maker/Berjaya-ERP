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
