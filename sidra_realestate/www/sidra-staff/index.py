"""The old staff web app at /sidra-staff/, retired by decision G21 (14 Nov 2026).

Staff now use the Berjaya interface at /berjaya, so this page only redirects: guests to the
sign-in page (returning to /berjaya), Sidra staff to /berjaya. Signed-in people who are not Sidra
staff are refused, as before. The redirects are temporary (302): they depend on the session.
Codex's client files (public/staff, clients/staff) are not touched; the page is removed in its
own change once nobody reaches it any more.
"""

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=%2Fberjaya"
		raise frappe.Redirect(302)  # temporary: depends on the session, so browsers must not remember it
	roles = set(frappe.get_roles())
	if "System Manager" not in roles and not any(r.startswith("Sidra ") for r in roles):
		frappe.throw(_("The staff app is for Sidra staff"), frappe.PermissionError)
	frappe.local.flags.redirect_location = "/berjaya"
	raise frappe.Redirect(302)
