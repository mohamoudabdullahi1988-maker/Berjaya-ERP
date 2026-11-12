"""Issue #3: fill the new collections-rule settings on existing contract profiles.

Mohamoud, 9 Nov 2026: the rules the installment engine had to assume become profile settings,
seeded with the engine's assumptions. Only blank settings are filled, so a value management has
already chosen is kept. Contracts are not touched: each keeps the terms frozen when it was saved
(INS-20); a draft picks up the new settings through Revise Draft.
"""

import frappe

from sidra_realestate.sidra_installments.doctype.sidra_contract_profile.sidra_contract_profile import (
	COLLECTION_RULE_DEFAULTS,
)


def execute():
	for name in frappe.get_all("Sidra Contract Profile", pluck="name"):
		current = frappe.db.get_value(
			"Sidra Contract Profile", name, list(COLLECTION_RULE_DEFAULTS), as_dict=True
		)
		updates = {
			field: value
			for field, value in COLLECTION_RULE_DEFAULTS.items()
			if current.get(field) in (None, "")
		}
		if updates:
			frappe.db.set_value("Sidra Contract Profile", name, updates)
