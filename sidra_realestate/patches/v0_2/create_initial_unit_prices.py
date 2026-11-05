"""Give every unit that has a cash price but no price history a first entry (SAL-02).

Units created before the price history existed keep their price; the entry takes effect
on the unit's creation date, so the history starts where the unit's record starts.
"""

import frappe

from sidra_realestate.services.prices import create_initial_price


def execute():
	priced = frappe.get_all("Sidra Unit", filters={"cash_price": (">", 0)}, fields=["name", "creation"])
	for row in priced:
		if frappe.db.exists("Sidra Unit Price History", {"unit": row.name, "docstatus": 1}):
			continue
		create_initial_price(frappe.get_doc("Sidra Unit", row.name), effective_from=row.creation)
