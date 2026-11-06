"""Unit status changes made by services (SRS v2.0 §2.3: status controlled by services).

Lock order (review finding 2): every service locks Sidra Unit rows first, in ascending
name order when it needs several (`lock_units`), and only then the Sidra Reservation row.
Reserve, cancel, expire and contract submission all follow it, so two of them can wait
for each other but never deadlock.
"""

import frappe
from frappe import _


class UnitNotAvailable(frappe.ValidationError):
	pass


def lock_unit(unit_name: str):
	"""Return the unit document with its row locked until the transaction ends."""
	if not unit_name or not frappe.db.exists("Sidra Unit", unit_name):
		frappe.throw(_("Unknown unit {0}").format(unit_name), frappe.DoesNotExistError)
	return frappe.get_doc("Sidra Unit", unit_name, for_update=True)


def lock_units(unit_names) -> list:
	"""Lock several units in ascending name order; returns them in that order."""
	return [lock_unit(name) for name in sorted(set(unit_names))]


def set_unit_status(unit, status: str, **values) -> None:
	"""Change a locked unit's status as a service. `unit` comes from `lock_unit`."""
	unit.status = status
	for field, value in values.items():
		unit.set(field, value)
	unit.flags.status_by_service = True
	unit.save(ignore_permissions=True)
