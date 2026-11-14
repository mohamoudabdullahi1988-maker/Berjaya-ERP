"""The Sidra front page at /sidra (docs/SHELL_v0.1.md).

One page staff reach after signing in: the executive dashboard, financial reports and the Real
Estate and Construction workflows. Server-rendered and read-only; not cached, because the counts
are the signed-in user's own. Guests go to the login page; signed-in people who are not Sidra
staff go to the desk they already have.
"""

import frappe

from sidra_realestate import __version__
from sidra_realestate.api.shell import DESK, build_shell, is_staff
from sidra_realestate.branding import APP_ICON, BRAND_NAME, ICON

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=%2Fsidra"
		raise frappe.Redirect(302)  # temporary: depends on the session, so browsers must not remember it
	if not is_staff():
		frappe.local.flags.redirect_location = DESK
		raise frappe.Redirect(302)  # temporary: depends on the session, so browsers must not remember it
	context.update(build_shell())
	context.brand_name = BRAND_NAME
	context.brand_icon = APP_ICON
	context.favicon = ICON
	context.asset_version = __version__
	context.no_cache = 1
	return context
