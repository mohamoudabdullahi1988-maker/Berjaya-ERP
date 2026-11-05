# Copyright (c) 2026, Mohamoud Abdullahi Sheikh

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SidraReservation(Document):
	def validate(self):
		if not self.flags.via_service:
			frappe.throw(
				_("Reservations are created and closed with the Reserve Unit action"), frappe.PermissionError
			)
		if getdate(self.expires_on) < getdate(self.reserved_on):
			frappe.throw(_("A reservation cannot expire before it starts"))

	def on_trash(self):
		frappe.throw(_("Reservations are kept for the audit trail; cancel them instead"))
