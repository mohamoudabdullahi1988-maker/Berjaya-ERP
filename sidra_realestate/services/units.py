"""Unit status changes made by services (SRS v2.0 §2.3: status controlled by services).

Every caller locks the unit row first (`lock_unit`) so reservation and contract
allocation serialise on the Sidra Unit row.
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


def set_unit_status(unit, status: str, **values) -> None:
	"""Change a locked unit's status as a service. `unit` comes from `lock_unit`."""
	unit.status = status
	for field, value in values.items():
		unit.set(field, value)
	unit.flags.status_by_service = True
	unit.save(ignore_permissions=True)
