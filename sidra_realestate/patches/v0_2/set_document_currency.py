"""Fill the new `currency` field on contracts and construction jobs from their Company.

Money fields used to name "USD" as a currency field, which Frappe ignores, so amounts showed
in the site's default currency. Display only: no amount changes.
"""

import frappe


def execute():
	for doctype in ("Sidra Sale Contract", "Sidra Construction Job"):
		for row in frappe.get_all(
			doctype, filters={"currency": ("is", "not set")}, fields=["name", "company"]
		):
			currency = frappe.get_cached_value("Company", row.company, "default_currency")
			frappe.db.set_value(doctype, row.name, "currency", currency, update_modified=False)
