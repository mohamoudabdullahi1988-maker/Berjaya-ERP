# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Unit Price History (SAL-02; SRS v2.0 §4.1). Rules under review in issue #6.

- Submitted entries are never edited or deleted.
- A new entry must take effect after the unit's latest submitted entry, so history
  cannot be rewritten by back-dating.
- Only an entry that is not yet in force can be cancelled.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from sidra_realestate.services.prices import latest_entry, refresh_unit_price
from sidra_realestate.services.units import lock_unit


class SidraUnitPriceHistory(Document):
	def validate(self):
		if not self.flags.ignore_permissions:
			# The company is fetched from the unit after Frappe's create check, so check the unit itself.
			frappe.get_doc("Sidra Unit", self.unit).check_permission("write")
		if flt(self.price, 2) <= 0:
			frappe.throw(_("The price must be greater than zero"))
		if not (self.reason or "").strip():
			frappe.throw(_("Give a reason for the price"))
		self.check_after_latest()

	def check_after_latest(self):
		latest = latest_entry(self.unit, exclude=self.name if not self.is_new() else None)
		if latest and getdate(self.effective_from) <= getdate(latest.effective_from):
			frappe.throw(
				_(
					"Unit {0} already has a price from {1} ({2}); a new price must take effect after that date"
				).format(self.unit, frappe.format(latest.effective_from, "Date"), latest.name)
			)

	def before_submit(self):
		lock_unit(self.unit)  # serialise price changes on the unit row
		self.check_after_latest()
		latest = latest_entry(self.unit, exclude=self.name)
		self.previous_price = flt(latest.price, 2) if latest else 0

	def on_submit(self):
		refresh_unit_price(self.unit)

	def before_cancel(self):
		if getdate(self.effective_from) <= getdate(today()):
			frappe.throw(
				_("A price already in force cannot be cancelled; enter a new price with a reason instead")
			)

	def on_cancel(self):
		refresh_unit_price(self.unit)
