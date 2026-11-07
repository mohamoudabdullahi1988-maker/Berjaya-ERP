"""Contract capture migration (docs/CONTRACT-CAPTURE_v0.3.md §6.3).

Every existing contract was made from a profile: installment contracts become
`source = Generated from profile`, their schedule rows `row_type = Installment`, and their
down-payment mode follows the stored down payment. Submitted contracts get their schedule
totals. No amount, date or frozen term changes. Cash contracts have no source.
"""

import frappe
from frappe.utils import flt


def execute():
	contracts = frappe.get_all(
		"Sidra Sale Contract",
		filters={"contract_type": "Installment"},
		fields=["name", "down_payment", "balance", "docstatus"],
	)
	for c in contracts:
		values = {
			"source": "Generated from profile",
			"down_payment_mode": "Recorded separately" if flt(c.down_payment) else "None",
		}
		if c.docstatus == 1:
			total = flt(
				frappe.db.sql(
					"select sum(amount) from `tabSidra Installment Line` where parenttype=%s and parent=%s",
					("Sidra Sale Contract", c.name),
				)[0][0],
				2,
			)
			values.update(
				schedule_total=total,
				amount_due=flt(c.balance, 2),
				schedule_difference=flt(flt(c.balance) - total, 2),
			)
		frappe.db.set_value("Sidra Sale Contract", c.name, values, update_modified=False)

	frappe.db.sql(
		"""update `tabSidra Installment Line` set row_type='Installment'
		where parenttype='Sidra Sale Contract' and ifnull(row_type, '')=''"""
	)
