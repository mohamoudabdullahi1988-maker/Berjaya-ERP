"""Unit reservations (SAL-04; SRS v2.0 §3.2 reservation workflow, §6 API).

Reservations are made only through `reserve_unit`, which locks the unit row, so two
users reserving the same unit at once cannot both win. A reservation records no money:
the deposit needs a native ERPNext Payment Entry, which is outside P0.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from sidra_realestate.services.units import UnitNotAvailable, lock_unit, set_unit_status

RESERVE_ROLES = ("Sidra Sales User", "Sidra Sales Manager")
DEFAULT_DAYS = 7  # SRS v1.6 §4.2


@frappe.whitelist(methods=["POST"])
def reserve_unit(unit_name: str, customer: str, days: int | None = None) -> dict:
	frappe.only_for(RESERVE_ROLES)

	days = DEFAULT_DAYS if days in (None, "") else cint(days)
	if days < 1:
		frappe.throw(_("A reservation must last at least one day"))
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(_("Unknown customer {0}").format(customer), frappe.DoesNotExistError)

	unit = lock_unit(unit_name)
	unit.check_permission("read")  # per-Company user permissions; the insert below skips them
	if unit.status != "Available":
		frappe.throw(
			_("Unit {0} is {1} and cannot be reserved").format(unit.name, unit.status), UnitNotAvailable
		)

	reserved_on = getdate(today())
	reservation = frappe.new_doc("Sidra Reservation")
	reservation.update(
		{
			"unit": unit.name,
			"customer": customer,
			"company": unit.company,
			"reserved_on": reserved_on,
			"expires_on": add_days(reserved_on, days),
			"status": "Active",
		}
	)
	reservation.flags.via_service = True
	reservation.insert(ignore_permissions=True)

	set_unit_status(unit, "Reserved", current_reservation=reservation.name)
	return {"reservation": reservation.name, "expires_on": str(reservation.expires_on)}


@frappe.whitelist(methods=["POST"])
def cancel_reservation(reservation: str) -> None:
	frappe.only_for(RESERVE_ROLES)
	if not reservation or not frappe.db.exists("Sidra Reservation", reservation):
		frappe.throw(_("Unknown reservation {0}").format(reservation), frappe.DoesNotExistError)
	frappe.get_doc("Sidra Reservation", reservation).check_permission("read")
	if not _close(reservation, "Cancelled"):
		frappe.throw(_("Only an active reservation can be cancelled"))


def expire_reservations() -> None:
	"""Daily scheduler job: expire reservations whose last day has passed."""
	stale = frappe.get_all(
		"Sidra Reservation",
		filters={"status": "Active", "expires_on": ("<", today())},
		pluck="name",
		order_by="expires_on asc",
	)
	for name in stale:
		_close(name, "Expired")


def _close(name: str, status: str) -> bool:
	"""Close an active reservation; release the unit only if this reservation still holds it.

	Locks the unit, then the reservation (see services/units.py), and re-reads the
	reservation under the lock: a contract may have converted it meanwhile.
	Returns False if it was no longer active.
	"""
	unit = lock_unit(frappe.db.get_value("Sidra Reservation", name, "unit"))
	reservation = frappe.get_doc("Sidra Reservation", name, for_update=True)
	if reservation.status != "Active":
		return False
	reservation.status = status
	reservation.flags.via_service = True
	reservation.save(ignore_permissions=True)
	if unit.status == "Reserved" and unit.current_reservation == reservation.name:
		set_unit_status(unit, "Available", current_reservation=None)
	return True
