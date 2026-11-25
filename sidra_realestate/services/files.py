# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Private attachment checks shared by Sidra records (SRS v2.0 §8: no public customer files)."""

import frappe
from frappe import _


def check_own_private_file(doc, fieldname, label):
	"""The file in `fieldname` must be uploaded to this record's own field, private, and used nowhere else.

	Same rule as the sale contract's signed copy (review finding 1 on develop @ cbce4f3).
	"""
	file_url = doc.get(fieldname)
	files = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=["name", "attached_to_doctype", "attached_to_name", "attached_to_field"],
	)
	own = [
		f
		for f in files
		if (f.attached_to_doctype, f.attached_to_name, f.attached_to_field)
		== (doc.doctype, doc.name, fieldname)
	]
	if not own:
		frappe.throw(_("Upload the {0} to this record's own field and save before submitting").format(label))
	if len(own) != len(files):
		frappe.throw(
			_("This {0} file is also used by another record; upload this record's own copy").format(label),
			frappe.PermissionError,
		)
	file_doc = frappe.get_doc("File", own[0].name)
	if not file_doc.is_private:
		frappe.throw(_("The {0} must be a private file").format(label))
	if not file_doc.has_permission("read"):
		frappe.throw(_("You cannot read this {0}").format(label), frappe.PermissionError)
	if not file_doc.exists_on_disk():
		frappe.throw(_("The {0} file is missing from the server; upload it again").format(label))
