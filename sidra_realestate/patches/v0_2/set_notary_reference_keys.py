"""Fill `notary_reference_key` for contracts signed before the unique index (review finding 3).

Runs after the column and its unique index exist (all values empty). Stops with a clear
message if two signed contracts already share a reference, so the duplicate is resolved
by a person rather than silently dropped.
"""

import frappe

from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import (
	normalize_notary_reference,
)


def execute():
	signed = frappe.get_all(
		"Sidra Sale Contract",
		filters={"docstatus": 1, "notary_reference_key": ("is", "not set")},
		fields=["name", "notary_reference"],
		order_by="creation asc",
	)
	seen = {}
	for row in signed:
		key = normalize_notary_reference(row.notary_reference)
		if not key:
			continue
		if key in seen:
			frappe.throw(
				f"Signed contracts {seen[key]} and {row.name} share notary reference {key}; "
				"resolve this before migrating"
			)
		seen[key] = row.name
	for key, name in seen.items():
		frappe.db.set_value("Sidra Sale Contract", name, "notary_reference_key", key, update_modified=False)
