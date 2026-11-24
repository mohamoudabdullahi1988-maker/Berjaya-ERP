# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G32: access to a buyer's identity record needs General Manager approval for that buyer.

No approval record exists yet, so no one may grant access to a `Sidra Customer KYC` record by
sharing it. Berjaya already refuses the share (api/record_tools.py); since G36 opened Desk to
staff, this check runs on the share itself, so Desk's Share button, "everyone" shares and the
automatic share Frappe makes when a record is assigned to someone who cannot read it are refused
too. Removing a share is always allowed. Role permissions on the DocType are unchanged.
"""

import frappe
from frappe import _

KYC = "Sidra Customer KYC"


def refuse_kyc_share(doc, method=None):
	if doc.share_doctype != KYC:
		return
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if not any(doc.get(right) for right in ("read", "write", "share", "submit")):
		return
	frappe.throw(
		_("Identity access requires General Manager approval for this buyer (G32)"),
		frappe.PermissionError,
	)
