"""The old staff front page at /sidra (docs/SHELL_v0.1.md, decision G15), retired by decision G21.

Staff now start in the Berjaya interface at /berjaya, so this page only redirects: guests to the
sign-in page (returning to /berjaya), Sidra staff to /berjaya, and signed-in people who are not
Sidra staff to the desk they already have. The redirects are temporary (302): they depend on the
session. The shell's data (api/shell.py) stays for the tests and reports that use it.
"""

import frappe

from sidra_realestate.api.shell import DESK, is_staff

BERJAYA = "/berjaya"

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=%2Fberjaya"
	elif is_staff():
		frappe.local.flags.redirect_location = BERJAYA
	else:
		frappe.local.flags.redirect_location = DESK
	raise frappe.Redirect(302)  # temporary: depends on the session, so browsers must not remember it
