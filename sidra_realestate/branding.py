"""Product branding and navigation (white-label; no Frappe or ERPNext core edits).

The software is **Berjaya**; **Sidra** is the company using it (decisions G17-G19). `BRAND_NAME`
is the single source of the product name: hooks, pages and tests read it from here. Company
records, print letterheads and internal identifiers keep the Sidra name and are not touched here.

- Logo, favicon and system name: Navbar Settings, Website Settings and System Settings get the
  product name and wordmark on install and migrate. A value an administrator has changed to
  something other than a Frappe / ERPNext default, or this app's own earlier branding, is left
  alone.
- Front page: System Settings "Default App" is set to this app when it is blank, so staff land
  on /sidra after signing in (decision G15). A choice an administrator has made is left alone,
  and so is each user's own default app.
- Navigation: the app ships a Dock (`dock/`) and two Sidebars (`sidebar/`): Real Estate and
  Construction. ERPNext modules Sidra does not use are hidden for staff through the Module Profile
  "Sidra Staff" (hidden, not deleted; administrators still see them).
"""

import frappe

BRAND_NAME = "Berjaya"
# Wordmark and icon in the decided colours (G20: charcoal and terracotta), the same mark the
# /berjaya interface draws. The sign-in page is styled by public/css/berjaya-login.css (hooks.py).
LOGO = "/assets/sidra_realestate/images/berjaya-wordmark.png"
ICON = "/assets/sidra_realestate/images/berjaya-favicon.png"
APP_ICON = "/assets/sidra_realestate/images/berjaya-icon.png"
# The company's own logo: letterhead on contracts and quotations. Client identity, never replaced.
COMPANY_LOGO = "/assets/sidra_realestate/images/sidra-logo.png"

# What this app itself wrote as product branding before G18. Only these exact settings values
# are replaced on migrate; Company records are never read or written here.
_PREVIOUS_BRANDING = (
	"Sidra Homes",
	"/assets/sidra_realestate/images/sidra-logo.png",
	"/assets/sidra_realestate/images/favicon.png",
)

MODULE_PROFILE = "Sidra Staff"
# Decision of 7 Nov 2026 (Mohamoud): hidden for Sidra staff. Accounts, Selling and CRM stay.
HIDDEN_MODULES = (
	"Manufacturing",
	"Stock",
	"Projects",
	"Buying",
	"Quality Management",
	"Support",
	"Assets",
	"Subcontracting",
	"Maintenance",
)

_DEFAULT_MARKERS = ("frappe", "erpnext")


def _replaceable(value) -> bool:
	if not value or str(value) in _PREVIOUS_BRANDING:
		return True
	return any(marker in str(value).lower() for marker in _DEFAULT_MARKERS)


def _set_single(doctype, values):
	meta = frappe.get_meta(doctype)
	for field, value in values.items():
		if not meta.has_field(field):
			continue
		if _replaceable(frappe.db.get_single_value(doctype, field)):
			frappe.db.set_single_value(doctype, field, value)


def apply_branding():
	_set_single("System Settings", {"app_name": BRAND_NAME})
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "sidra_realestate")
	_set_single("Navbar Settings", {"app_logo": LOGO})
	_set_single(
		"Website Settings",
		{"app_name": BRAND_NAME, "app_logo": LOGO, "favicon": ICON, "footer_powered": BRAND_NAME},
	)
	ensure_module_profile()
	frappe.clear_cache()


def ensure_module_profile():
	modules = [m for m in HIDDEN_MODULES if frappe.db.exists("Module Def", m)]
	if frappe.db.exists("Module Profile", MODULE_PROFILE):
		profile = frappe.get_doc("Module Profile", MODULE_PROFILE)
		present = {row.module for row in profile.block_modules}
		missing = [m for m in modules if m not in present]
		if not missing:
			return
		for module in missing:
			profile.append("block_modules", {"module": module})
		profile.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "Module Profile",
			"module_profile_name": MODULE_PROFILE,
			"block_modules": [{"module": m} for m in modules],
		}
	).insert(ignore_permissions=True)


def has_app_permission() -> bool:
	"""Show the app icon to Sidra staff and system managers."""
	roles = set(frappe.get_roles())
	return "System Manager" in roles or any(role.startswith("Sidra ") for role in roles)
