# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Contract settings (decision D3, issue #13): the schedule tolerance for registered contracts."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

DEFAULT_SCHEDULE_TOLERANCE = 5.0


class SidraContractSettings(Document):
	def validate(self):
		if flt(self.schedule_tolerance, 2) < 0:
			frappe.throw(_("The schedule tolerance cannot be negative"))


def _stored():
	"""The stored value, or None when the setting has never been saved (get_single_value casts None to 0)."""
	return frappe.db.get_value(
		"Singles", {"doctype": "Sidra Contract Settings", "field": "schedule_tolerance"}, "value"
	)


def schedule_tolerance() -> float:
	value = _stored()
	return DEFAULT_SCHEDULE_TOLERANCE if value is None else flt(value, 2)


def ensure_contract_settings():
	"""Store the default tolerance once, so the setting shows $5.00 until management changes it."""
	if _stored() is None:
		frappe.db.set_single_value(
			"Sidra Contract Settings", "schedule_tolerance", DEFAULT_SCHEDULE_TOLERANCE
		)
