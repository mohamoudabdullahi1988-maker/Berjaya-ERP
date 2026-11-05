"""Unit price history (SAL-02; SRS v2.0 §3.2, §4.1; issue #6).

A unit's cash price is the latest submitted Sidra Unit Price History entry whose
effective date is on or before the day asked about. `Sidra Unit.cash_price` mirrors
today's price and is written only by this module.
"""

import frappe
from frappe.utils import flt, getdate, today

from sidra_realestate.services.units import lock_unit

DOCTYPE = "Sidra Unit Price History"


def price_on(unit: str, on_date=None) -> float | None:
	"""The unit's cash price on `on_date` (default today), or None if no price was in force."""
	rows = frappe.get_all(
		DOCTYPE,
		filters={"unit": unit, "docstatus": 1, "effective_from": ("<=", getdate(on_date or today()))},
		fields=["price"],
		order_by="effective_from desc, creation desc",
		limit=1,
	)
	return flt(rows[0].price, 2) if rows else None


def latest_entry(unit: str, exclude: str | None = None):
	"""The submitted entry with the latest effective date, future-dated ones included."""
	filters = {"unit": unit, "docstatus": 1}
	if exclude:
		filters["name"] = ("!=", exclude)
	rows = frappe.get_all(
		DOCTYPE,
		filters=filters,
		fields=["name", "effective_from", "price"],
		order_by="effective_from desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def refresh_unit_price(unit_name: str) -> None:
	"""Set the unit's cash price to today's price from its history."""
	unit = lock_unit(unit_name)
	current = price_on(unit_name) or 0
	if flt(unit.cash_price, 2) != current:
		unit.cash_price = current
		unit.flags.price_by_service = True
		unit.flags.status_by_service = True  # status unchanged; skip the manual-status check
		unit.save(ignore_permissions=True)


def create_initial_price(unit, effective_from=None) -> str:
	"""First history entry for a unit created with a cash price."""
	entry = frappe.new_doc(DOCTYPE)
	entry.update(
		{
			"unit": unit.name,
			"effective_from": getdate(effective_from or today()),
			"price": flt(unit.cash_price, 2),
			"reason": "Initial price",
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()
	return entry.name


def refresh_current_prices() -> None:
	"""Daily scheduler job: bring each unit's cash price in line with its history."""
	units = frappe.get_all(
		DOCTYPE,
		filters={"docstatus": 1, "effective_from": ("<=", today())},
		pluck="unit",
		distinct=True,
	)
	for unit in units:
		refresh_unit_price(unit)
