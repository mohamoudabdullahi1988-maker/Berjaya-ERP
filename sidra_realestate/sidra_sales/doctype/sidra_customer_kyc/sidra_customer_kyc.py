# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Customer KYC (SAL-07; SRS v2.0 §3.5, §5, §8; decision G12; docs/KYC-AND-TITLE_v0.1.md).

- One restricted record per Customer, separate from the Customer form: ID or passport, phone,
  address, guarantor details and private scans. Only Sidra sales roles and the General Manager
  have access; other roles that can open the Customer do not see it.
- Sales staff enter it; a Sidra Sales Manager verifies it (`verify_kyc`). Verification needs the
  scanned ID uploaded to this record as a private file.
- Changing any detail of a verified record returns it to Draft until it is verified again.
- A contract generated from a profile needs the buyer's verified KYC before it is submitted;
  registered (external) contracts do not (G12, D5).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from sidra_realestate.services.files import check_own_private_file

DETAIL_FIELDS = (
	"id_type",
	"id_number",
	"name_on_id",
	"id_expiry",
	"id_document",
	"phone",
	"address",
	"guarantor_name",
	"guarantor_phone",
	"guarantor_relationship",
	"guarantor_id_number",
	"guarantor_document",
)
TEXT_FIELDS = (
	"id_number",
	"name_on_id",
	"phone",
	"address",
	"guarantor_name",
	"guarantor_phone",
	"guarantor_relationship",
	"guarantor_id_number",
)
GUARANTOR_FIELDS = tuple(f for f in DETAIL_FIELDS if f.startswith("guarantor_"))
VERIFICATION_FIELDS = ("status", "verified_by", "verified_on")
SCANS = (("id_document", "scanned ID"), ("guarantor_document", "guarantor scanned ID"))


class SidraCustomerKYC(Document):
	def validate(self):
		if not frappe.db.exists("Customer", self.customer):
			frappe.throw(_("Unknown customer {0}").format(self.customer), frappe.DoesNotExistError)
		if not self.flags.ignore_permissions:
			frappe.get_doc("Customer", self.customer).check_permission("read")
		for field in TEXT_FIELDS:
			self.set(field, (self.get(field) or "").strip() or None)
		for field in ("id_number", "phone", "address"):
			if not self.get(field):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(field))))
		if any(self.get(f) for f in GUARANTOR_FIELDS) and not (self.guarantor_name and self.guarantor_phone):
			frappe.throw(_("Give the guarantor's name and phone"))
		self.check_scans_private()
		self.protect_verification()

	def check_scans_private(self):
		for field, label in SCANS:
			if not self.get(field):
				continue
			private = frappe.get_all("File", filters={"file_url": self.get(field)}, pluck="is_private")
			if not private or not all(private):
				frappe.throw(_("Upload the {0} as a private file").format(_(label)))

	def protect_verification(self):
		"""Only `verify_kyc` verifies; any change to a verified record needs verifying again."""
		if self.flags.verifying:
			return
		before = (
			None if self.is_new() else (self.get_doc_before_save() or frappe.get_doc(self.doctype, self.name))
		)
		for field in VERIFICATION_FIELDS:
			self.set(field, before.get(field) if before else None)
		if not before or before.status != "Verified":
			self.status = "Draft"
			self.verified_by = self.verified_on = None
		elif any(str(self.get(f) or "") != str(before.get(f) or "") for f in DETAIL_FIELDS):
			self.status = "Draft"
			self.verified_by = self.verified_on = None


@frappe.whitelist()
def verify_kyc(kyc: str):
	"""SAL-07 / G12: a Sidra Sales Manager verifies the buyer's KYC against the scanned ID."""
	frappe.only_for("Sidra Sales Manager")
	doc = frappe.get_doc("Sidra Customer KYC", kyc)
	doc.check_permission("write")
	if doc.status == "Verified":
		frappe.throw(_("This KYC record is already verified"))
	if not doc.id_document:
		frappe.throw(_("Attach the scanned ID before verifying"))
	for field, label in SCANS:
		if doc.get(field):
			check_own_private_file(doc, field, _(label))
	doc.status = "Verified"
	doc.verified_by = frappe.session.user
	doc.verified_on = now_datetime()
	doc.flags.verifying = True
	doc.save()
	return {"status": doc.status, "verified_by": doc.verified_by}


def has_verified_kyc(customer: str) -> bool:
	return bool(frappe.db.exists("Sidra Customer KYC", {"customer": customer, "status": "Verified"}))
