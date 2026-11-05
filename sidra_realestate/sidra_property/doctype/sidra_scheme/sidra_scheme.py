# Copyright (c) 2026, Mohamoud Abdullahi Sheikh

import frappe
from frappe import _
from frappe.model.document import Document


class SidraScheme(Document):
	def validate(self):
		before = self.get_doc_before_save()
		if before and before.company != self.company and frappe.db.exists("Sidra Unit", {"scheme": self.name}):
			frappe.throw(_("The company of a scheme with units cannot be changed"))
