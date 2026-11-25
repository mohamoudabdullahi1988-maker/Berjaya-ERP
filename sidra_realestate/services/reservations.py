"""Unit reservations (SAL-04; SRS v2.0 §3.2 reservation workflow, §6 API).

Reservations are made only through `reserve_unit`, which locks the unit row, so two
users reserving the same unit at once cannot both win. A reservation records no money:
the deposit needs a native ERPNext Payment Entry, which is outside P0.
"""

import re

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from sidra_realestate.services.units import UnitNotAvailable, lock_unit, set_unit_status

RESERVE_ROLES = ("Sidra Sales User", "Sidra Sales Manager")
DEFAULT_DAYS = 7  # SRS v1.6 §4.2


@frappe.whitelist(methods=["POST"])
def reserve_unit(unit_name: str, customer: str, days=None) -> dict:
	frappe.only_for(RESERVE_ROLES)

	# Preserve the raw value: Frappe/Pydantic would coerce JSON true to integer 1
	# before this check if days were annotated as int. Validate form strings here too.
	if days in (None, ""):
		days = DEFAULT_DAYS
	elif isinstance(days, bool) or not re.fullmatch(r"[0-9]+", str(days)):
		frappe.throw(_("Reservation days must be a whole number"))
	else:
		try:
			days = int(days)
		except ValueError:
			frappe.throw(_("Reservation days must be a whole number"))
	if days < 1:
		frappe.throw(_("A reservation must last at least one day"))
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(_("Unknown customer {0}").format(customer), frappe.DoesNotExistError)
	frappe.get_doc("Customer", customer).check_permission("read")
	reserved_on = getdate(today())
	try:
		expires_on = add_days(reserved_on, days)
	except OverflowError, ValueError:
		frappe.throw(_("Reservation expiry is outside the supported date range"))

	unit = lock_unit(unit_name)
	unit.check_permission("read")  # per-Company user permissions; the insert below skips them
	if unit.status != "Available":
		frappe.throw(
			_("Unit {0} is {1} and cannot be reserved").format(unit.name, unit.status), UnitNotAvailable
		)

	reservation = frappe.new_doc("Sidra Reservation")
	reservation.update(
		{
			"unit": unit.name,
			"customer": customer,
			"company": unit.company,
			"reserved_on": reserved_on,
			"expires_on": expires_on,
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
	if not _close(reservation, "Cancelled", check_permissions=True):
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


def _close(name: str, status: str, *, check_permissions=False) -> bool:
	"""Close an active reservation; release the unit only if this reservation still holds it.

	Locks the unit, then the reservation (see services/units.py), and re-reads the
	reservation under the lock: a contract may have converted it meanwhile.
	Returns False if it was no longer active.
	"""
	unit = lock_unit(frappe.db.get_value("Sidra Reservation", name, "unit"))
	reservation = frappe.get_doc("Sidra Reservation", name, for_update=True)
	if check_permissions:
		# Recheck the locked parents. Scheduler expiry is internal; user cancellation
		# requires both the action role above and access to the actual unit/reservation.
		unit.check_permission("read")
		reservation.check_permission("read")
	if reservation.status != "Active":
		return False
	reservation.status = status
	reservation.flags.via_service = True
	reservation.save(ignore_permissions=True)
	if unit.status == "Reserved" and unit.current_reservation == reservation.name:
		set_unit_status(unit, "Available", current_reservation=None)
	return True
