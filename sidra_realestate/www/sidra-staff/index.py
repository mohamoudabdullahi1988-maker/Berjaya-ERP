"""Staff web app at /sidra-staff/ (clients/staff/docs/API-CONTRACT.md, "Shared deployment").

Serves Codex's UI (clients/staff/web, published at /assets/sidra_realestate/staff/ through the
`public/staff` link) on the site's own origin, for signed-in Sidra staff only. The session's CSRF
token is put into `window.SIDRA_CONFIG` on every request (Frappe replaces `<!-- csrf_token -->`
after any page caching). The page is not cached. No secret is embedded.
"""

import os

import frappe
from frappe import _

ASSET_BASE = "/assets/sidra_realestate/staff/"
SCRIPT_MARK = '<script src="./config.js"></script>'

no_cache = 1


def _client_index() -> str:
	path = os.path.join(frappe.get_app_path("sidra_realestate"), "public", "staff", "index.html")
	with open(path, encoding="utf-8") as fh:
		return fh.read()


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=%2Fsidra-staff%2F"
		raise frappe.Redirect(302)  # temporary: depends on the session, so browsers must not remember it
	roles = set(frappe.get_roles())
	if "System Manager" not in roles and not any(r.startswith("Sidra ") for r in roles):
		frappe.throw(_("The staff app is for Sidra staff"), frappe.PermissionError)

	html = _client_index().replace("</body></html>", "").replace("</body>", "").replace("</html>", "")
	html = html.replace("<head>", f'<head><base href="{ASSET_BASE}">', 1)
	if SCRIPT_MARK not in html:
		frappe.throw(_("The staff app page has an unexpected layout"))
	before, after = html.split(SCRIPT_MARK, 1)
	context.staff_before = before
	context.staff_after = SCRIPT_MARK + after
	context.config = frappe.as_json(
		{
			"dashboardMethod": "sidra_realestate.api.staff_dashboard.get_dashboard",
			"locationsMethod": "sidra_realestate.api.locations",
		}
	)
	context.no_cache = 1
	return context
