"""Owner request, 12 Nov 2026: use Somaliland throughout the Sidra site."""

import frappe

from sidra_realestate.site_setup import ensure_country


def execute():
	country = ensure_country()
	previous = "Somalia"
	for doctype in ("System Settings", "Global Defaults"):
		if frappe.db.get_single_value(doctype, "country") == previous:
			frappe.db.set_single_value(doctype, "country", country)
	if frappe.db.get_default("country") == previous:
		frappe.db.set_default("country", country)
	for doctype in ("Company", "Address"):
		for name in frappe.get_all(doctype, filters={"country": previous}, pluck="name"):
			frappe.db.set_value(doctype, name, "country", country)

	# Native preset names are also displayed in address and customer forms.
	# Rename through Frappe so existing links follow the master, including on reruns.
	if frappe.db.exists("Address Template", previous):
		frappe.db.set_value("Address Template", previous, "country", country)
		frappe.rename_doc(
			"Address Template",
			previous,
			country,
			merge=bool(frappe.db.exists("Address Template", country)),
			force=True,
		)
	if frappe.db.exists("Territory", previous):
		frappe.rename_doc(
			"Territory",
			previous,
			country,
			merge=bool(frappe.db.exists("Territory", country)),
			force=True,
		)
	frappe.clear_cache()
