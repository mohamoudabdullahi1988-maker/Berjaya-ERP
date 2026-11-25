# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G32: access to a buyer's identity record needs General Manager approval for that buyer.

The approval is a Sidra KYC Access Request (sidra_sales/doctype/sidra_kyc_access_request). Its
`approve` method is the only way to share a `Sidra Customer KYC` record: it shares that one record
with that one person, read only, while the approval lasts. Every other share that grants access is
refused here, on the share itself: Desk's Share button, Berjaya's share action, "everyone" shares,
the automatic share Frappe makes when a record is assigned to someone who cannot read it, and any
attempt to add edit or re-share rights. Removing a share is always allowed. Role permissions on the
DocType are unchanged.
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
	if approved_share(doc):
		return
	frappe.throw(
		_("Identity access requires General Manager approval for this buyer (G32)"),
		frappe.PermissionError,
	)


def approved_share(doc):
	"""A read-only share for one person, made by the approval of a current request for them."""
	from sidra_realestate.sidra_sales.doctype.sidra_kyc_access_request.sidra_kyc_access_request import (
		approved_request,
	)

	request = doc.flags.get("sidra_kyc_access_request")
	if not request or doc.everyone or any(doc.get(right) for right in ("write", "share", "submit")):
		return False
	return bool(approved_request(request, doc.share_name, doc.user))
