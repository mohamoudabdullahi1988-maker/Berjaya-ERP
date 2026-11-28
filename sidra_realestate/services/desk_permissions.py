# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G44 (26 Nov 2026): who may open the native ERPNext records in Desk.

Added on top of ERPNext's own rules, never replacing them (after_install / after_migrate):
- Finance Review reads Quotations, Sales Orders, Projects, Tasks and Assets (no create or edit);
- General Management and Project Staff read the Assets register;
- Project Staff raise Material Requests for house stores and read Warehouses and Items. Stock
  moves stay refused until Finance approves the stock accounts (G42).
ERPNext Quotations and Sales Orders are only the copies of Sidra records (G40): one made by hand
is refused (`refuse_hand_made`).
Decision G45 (28 Nov 2026): General Management also reads Projects and Tasks (no create or edit).

Frappe keeps a DocType's permissions in one place once any is customised: the first grant copies
ERPNext's standard rules for that DocType into Custom DocPerm, then adds these. A later ERPNext
change to its standard rules for these DocTypes is therefore not picked up automatically.
"""

import frappe
from frappe import _

READ = ("read", "report", "print")
FINANCE = "Sidra Finance Reviewer"
GM = "Sidra General Manager"
PM = "Sidra Project Manager"

GRANTS = (
	("Quotation", FINANCE, READ),
	("Sales Order", FINANCE, READ),
	("Project", FINANCE, READ),
	("Task", FINANCE, READ),
	("Asset", FINANCE, READ),
	("Asset Category", FINANCE, ("read",)),
	("Asset", GM, READ),
	("Asset Category", GM, ("read",)),
	("Project", GM, READ),  # G45
	("Task", GM, READ),  # G45
	("Asset", PM, READ),
	("Asset Category", PM, ("read",)),
	("Material Request", PM, ("read", "write", "create", "submit", "report", "print")),
	("Warehouse", PM, ("read",)),
	("Item", PM, ("read",)),
)
COPY_FLAG = "sidra_selling_copy"


def ensure_desk_permissions():
	"""Add the grants that are missing. Idempotent; never removes or lowers a right."""
	from frappe.permissions import add_permission, update_permission_property

	for doctype, role, rights in GRANTS:
		if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", role):
			continue
		rule = frappe.db.get_value(
			"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}, "name"
		)
		if not rule:
			add_permission(doctype, role, 0, rights[0])
		for right in rights:
			if not frappe.db.get_value(
				"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}, right
			):
				update_permission_property(doctype, role, 0, right, 1, validate=False)
	frappe.clear_cache()


def refuse_hand_made(doc, method=None):
	"""before_insert on Quotation and Sales Order: only the G40 copies of Sidra records."""
	if frappe.flags.get(COPY_FLAG) or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	frappe.throw(
		_(
			"ERPNext {0}s are made from Sidra records: issue a Sidra quotation or confirm a Sidra "
			"contract instead (decision G44)"
		).format(_(doc.doctype)),
		frappe.PermissionError,
		title=_("Made from Sidra records only"),
	)
