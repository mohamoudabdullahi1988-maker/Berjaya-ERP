"""Finance verification for a posted invoice. The document owner records the verifier."""

import frappe
from frappe import _
from frappe.model.document import Document


class SidraAgreementInvoice(Document):
	def validate(self):
		if not self.is_new() or not self.flags.finance_verified:
			frappe.throw(_("Use Finance verification to link a posted invoice"), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("A Finance-verified invoice link cannot be deleted"), frappe.PermissionError)
