"""Site regional settings from NFR-10 (USD, DD/MM/YYYY, Africa/Mogadishu). Run once per site:

	bench --site <site> execute sidra_realestate.site_setup.apply_regional_settings

Saves System Settings and the matching site defaults (Frappe reads the date format from the
defaults). Users keep their own time-zone preference: set it per user, or create users after
this runs. Changes no business data. Safe to run again.
"""

import frappe

REGIONAL = {
	"country": "Somaliland",
	"time_zone": "Africa/Mogadishu",
	"date_format": "dd/mm/yyyy",
	"currency": "USD",
}


def ensure_country() -> str:
	"""Provide the country link before settings, companies or native presets use it."""
	country = REGIONAL["country"]
	if not frappe.db.exists("Country", country):
		frappe.get_doc(
			{
				"doctype": "Country",
				"country_name": country,
				# Keep the existing regional ISO code; do not invent a country code.
				"code": "so",
				"date_format": REGIONAL["date_format"],
				"time_zones": REGIONAL["time_zone"],
			}
		).insert(ignore_permissions=True)
	return country


def apply_regional_settings() -> dict:
	ensure_country()
	settings = frappe.get_single("System Settings")
	settings.update(REGIONAL)
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
	for key in ("currency", "date_format", "time_zone"):
		frappe.db.set_default(key, REGIONAL[key])
	frappe.db.commit()
	frappe.clear_cache()
	return {key: settings.get(key) for key in REGIONAL}
