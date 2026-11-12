import frappe

from sidra_realestate.desk_setup import repair_desk
from sidra_realestate.services.prices import refresh_current_prices


def execute():
	for unit in frappe.get_all("Sidra Unit", fields=["name", "scheme"]):
		frappe.db.set_value("Sidra Unit", unit.name, "scheme_code", frappe.db.get_value("Sidra Scheme", unit.scheme, "scheme_code"), update_modified=False)
	refresh_current_prices()
	repair_desk()
