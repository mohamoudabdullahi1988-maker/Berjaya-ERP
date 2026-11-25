# Copyright (c) 2026, Mohamoud Abdullahi Sheikh

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from sidra_realestate.services.prices import create_initial_price

# A person may switch a unit only between these two (SRS v1.6 §4.2: Blocked is set by management).
MANUAL_STATUSES = {"Available", "Blocked"}
MANUAL_STATUS_ROLES = {"Sidra Sales Manager", "Sidra General Manager"}


class SidraUnit(Document):
	def validate(self):
		self.company = frappe.db.get_value("Sidra Scheme", self.scheme, "company")
		self.scheme_code = frappe.db.get_value("Sidra Scheme", self.scheme, "scheme_code")
		for field in ("district", "neighbourhood"):
			canonical = frappe.db.get_value("Sidra Scheme", self.scheme, field)
			if canonical:
				self.set(field, canonical.strip())
		self.validate_status_change()
		self.validate_price_change()
		self.validate_scheme_change()
		for field in ("area_sqm", "cash_price", "bedrooms", "floors"):
			if (self.get(field) or 0) < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)))

	def validate_price_change(self):
		before = self.get_doc_before_save()
		if before is None or self.flags.price_by_service:
			return
		if flt(before.cash_price, 2) != flt(self.cash_price, 2):
			frappe.throw(_("Change a unit's price with a Unit Price History entry (SAL-02)"))

	def validate_scheme_change(self):
		"""Review finding 4: a scheme move must not invalidate records that point at this unit.

		- Any move is refused once the unit is on a submitted contract (the signed contract
			describes the unit in its scheme).
		- A move into another Company's scheme is refused if the unit has any reservation,
			any contract (draft included) or any price history, because those records carry
			the old Company.
		"""
		before = self.get_doc_before_save()
		if before is None or before.scheme == self.scheme:
			return
		if frappe.db.exists("Sidra Contract Unit", {"unit": self.name, "docstatus": 1}):
			frappe.throw(_("Unit {0} is on a signed contract; its scheme cannot change").format(self.name))
		if before.company == self.company:
			return
		blockers = [
			label
			for doctype, label in (
				("Sidra Reservation", _("reservations")),
				("Sidra Contract Unit", _("contracts")),
				("Sidra Unit Price History", _("price history")),
			)
			if frappe.db.exists(doctype, {"unit": self.name})
		]
		if blockers:
			frappe.throw(
				_("Unit {0} cannot move from {1} to {2}: it has {3} under {1}").format(
					self.name, before.company, self.company, ", ".join(blockers)
				)
			)

	def after_insert(self):
		if flt(self.cash_price, 2) > 0:
			create_initial_price(self)

	def validate_status_change(self):
		if self.flags.status_by_service:
			return

		before = self.get_doc_before_save()
		if before is None:
			if self.status not in MANUAL_STATUSES:
				frappe.throw(_("A new unit must be Available or Blocked"))
			self.current_reservation = self.current_contract = None
			return

		for field in ("current_reservation", "current_contract"):
			if before.get(field) != self.get(field):
				frappe.throw(_("{0} is set by reservations and contracts").format(self.meta.get_label(field)))

		if before.status == self.status:
			return
		if {before.status, self.status} != MANUAL_STATUSES:
			frappe.throw(
				_(
					"Unit status {0} is set by reservations and contracts; it cannot be changed to {1} by hand"
				).format(before.status, self.status)
			)
		if not MANUAL_STATUS_ROLES.intersection(frappe.get_roles()):
			frappe.throw(
				_("Only a Sales Manager or General Manager can block or release a unit"),
				frappe.PermissionError,
			)
