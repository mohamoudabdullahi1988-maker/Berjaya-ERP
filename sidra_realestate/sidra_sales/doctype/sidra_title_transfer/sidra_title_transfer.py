# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Title Transfer (SAL-08, SAL-18; decision G12; docs/KYC-AND-TITLE_v0.1.md).

A record of the title process for one unit of a confirmed sale contract. Record only: it never
changes the unit, the contract or ownership, and calculates no delay amount (CLAUDE.md rule 3).

- Final payment: until receipts exist (P2), a Sidra Sales Manager enters the final payment date
  with private evidence, and a different Sales Manager confirms it (`confirm_final_payment`).
  The deadline is then the contract's frozen title deadline days after that date.
- Status follows the deadline: Due Soon from 5 days before it, Overdue after it, with the number
  of days past the deadline. A daily job keeps it current.
- Documents required, land office submission, deed number and handover are recorded as they happen.
- Handover: the General Manager confirms it (`confirm_handover`), and cannot be the person who
  entered it. It needs the deed number, date, recipient and the customer's signed receipt as a
  private file. After that the record is locked.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime, today

from sidra_realestate.services.files import check_own_private_file
from sidra_realestate.services.title import HANDED_OVER, HANDED_OVER_LATE, deadline_date, title_state

DOCTYPE = "Sidra Title Transfer"
CONTRACT = "Sidra Sale Contract"
PAYMENT_FIELDS = ("final_payment_date", "final_payment_evidence")
HANDOVER_FIELDS = ("deed_number", "deed_issued_on", "handed_over_on", "handed_over_to", "handover_evidence")
SYSTEM_FIELDS = (
	"final_payment_entered_by",
	"final_payment_confirmed_by",
	"final_payment_confirmed_on",
	"handover_entered_by",
	"handover_confirmed_by",
	"handover_confirmed_on",
)
PAST_DATES = ("final_payment_date", "submitted_on", "deed_issued_on", "handed_over_on")


def _same(a, b):
	return str(a or "") == str(b or "")


class SidraTitleTransfer(Document):
	def validate(self):
		before = None if self.is_new() else (self.get_doc_before_save() or frappe.get_doc(DOCTYPE, self.name))
		if before and before.handover_confirmed_on and not self.flags.confirming:
			frappe.throw(_("The deed was handed over and confirmed; this record can no longer be changed"))
		contract = self.set_contract_fields()
		self.protect_confirmations(before)
		self.validate_dates(contract)
		self.validate_documents()
		self.set_state()

	def set_contract_fields(self):
		contract = frappe.get_doc(CONTRACT, self.contract)
		if not self.flags.ignore_permissions:
			contract.check_permission("read")
		if contract.docstatus != 1:
			frappe.throw(
				_("Contract {0} is not confirmed; title is tracked only for confirmed contracts").format(
					self.contract
				)
			)
		if self.unit not in [row.unit for row in contract.units]:
			frappe.throw(_("Unit {0} is not on contract {1}").format(self.unit, self.contract))
		self.customer = contract.customer
		self.company = contract.company
		self.contract_unit_key = f"{self.contract}::{self.unit}"
		duplicate = frappe.db.get_value(
			DOCTYPE, {"contract_unit_key": self.contract_unit_key, "name": ("!=", self.name or "")}
		)
		if duplicate:
			frappe.throw(
				_("Title record {0} already tracks unit {1} of this contract").format(duplicate, self.unit)
			)
		terms = contract.terms() or {}
		self.title_deadline_days = cint(contract.title_deadline_days or terms.get("title_deadline_days"))
		self.title_term = title_term_text(contract, terms)
		return contract

	def protect_confirmations(self, before):
		"""Who entered and who confirmed are set by the system, and confirmed facts are frozen."""
		user = frappe.session.user
		if not self.flags.confirming:
			for field in SYSTEM_FIELDS:
				self.set(field, before.get(field) if before else None)
		payment_changed = any(
			not _same(self.get(f), before.get(f) if before else None) for f in PAYMENT_FIELDS
		)
		handover_changed = any(
			not _same(self.get(f), before.get(f) if before else None) for f in HANDOVER_FIELDS
		)
		if payment_changed:
			if before and before.final_payment_confirmed_on:
				frappe.throw(
					_("The final payment is confirmed; its date and evidence can no longer be changed")
				)
			self.final_payment_entered_by = user
		if handover_changed:
			self.handover_entered_by = user

	def validate_dates(self, contract):
		for field in PAST_DATES:
			if self.get(field) and getdate(self.get(field)) > getdate(today()):
				frappe.throw(_("{0} cannot be in the future").format(_(self.meta.get_label(field))))
		paid = self.final_payment_date and getdate(self.final_payment_date)
		if paid and contract.signed_on and paid < getdate(contract.signed_on):
			frappe.throw(_("The final payment cannot be before the contract date"))
		if paid and self.handed_over_on and getdate(self.handed_over_on) < paid:
			frappe.throw(_("The deed cannot be handed over before the final payment"))

	def validate_documents(self):
		for row in self.documents:
			if row.received_on and not row.received:
				frappe.throw(_("Documents row {0}: tick Received or clear the date").format(row.idx))
			if row.received_on and getdate(row.received_on) > getdate(today()):
				frappe.throw(
					_("Documents row {0}: the received date cannot be in the future").format(row.idx)
				)
			if row.file:
				private = frappe.get_all("File", filters={"file_url": row.file}, pluck="is_private")
				if not private or not all(private):
					frappe.throw(_("Documents row {0}: upload the file as a private file").format(row.idx))

	def set_state(self, on_date=None):
		confirmed = bool(self.final_payment_confirmed_on)
		paid = getdate(self.final_payment_date) if confirmed and self.final_payment_date else None
		deadline = deadline_date(paid, self.title_deadline_days)
		handed = getdate(self.handed_over_on) if self.handover_confirmed_on and self.handed_over_on else None
		self.deadline_date = deadline
		self.status, self.days_overdue = title_state(getdate(on_date or today()), confirmed, deadline, handed)

	def on_trash(self):
		if self.final_payment_confirmed_on:
			frappe.throw(_("A title record with a confirmed final payment cannot be deleted"))


def title_term_text(contract, terms) -> str:
	"""The contract's frozen late-title term as text, for reference only. Nothing is calculated."""
	kind = contract.title_penalty_type or terms.get("title_penalty_type")
	amount = contract.title_penalty_amount or terms.get("title_penalty_amount")
	if not kind or kind == "None" or not amount:
		return _("No late-title term recorded on the contract")
	money = frappe.format(amount, {"fieldtype": "Currency", "options": "currency"}, doc=contract)
	return _("{0}: {1} (from the contract; not calculated or applied here)").format(_(kind), money)


@frappe.whitelist()
def confirm_final_payment(title: str):
	"""SAL-18 / G12: a second Sidra Sales Manager confirms the final payment date and its evidence."""
	frappe.only_for("Sidra Sales Manager")
	doc = frappe.get_doc(DOCTYPE, title)
	doc.check_permission("write")
	if doc.final_payment_confirmed_on:
		frappe.throw(_("The final payment is already confirmed"))
	if not doc.final_payment_date:
		frappe.throw(_("Enter the final payment date"))
	if not doc.final_payment_evidence:
		frappe.throw(_("Attach the final payment evidence"))
	check_own_private_file(doc, "final_payment_evidence", _("final payment evidence"))
	if frappe.session.user == doc.final_payment_entered_by:
		frappe.throw(
			_(
				"A second Sales Manager confirms the final payment: {0} entered it and cannot confirm it"
			).format(doc.final_payment_entered_by),
			frappe.PermissionError,
			title=_("Second person needed"),
		)
	doc.final_payment_confirmed_by = frappe.session.user
	doc.final_payment_confirmed_on = now_datetime()
	doc.flags.confirming = True
	doc.save()
	return {"status": doc.status, "deadline_date": str(doc.deadline_date) if doc.deadline_date else None}


@frappe.whitelist()
def confirm_handover(title: str):
	"""SAL-08 / G12: the General Manager confirms the deed was handed to the customer. Record only."""
	frappe.only_for("Sidra General Manager")
	doc = frappe.get_doc(DOCTYPE, title)
	doc.check_permission("read")
	if doc.handover_confirmed_on:
		frappe.throw(_("The handover is already confirmed"))
	if not doc.final_payment_confirmed_on:
		frappe.throw(_("Confirm the final payment before the handover"))
	missing = [
		_(doc.meta.get_label(f))
		for f in ("deed_number", "handed_over_on", "handed_over_to", "handover_evidence")
		if not (str(doc.get(f) or "")).strip()
	]
	if missing:
		frappe.throw(_("Before confirming the handover, add: {0}").format(", ".join(missing)))
	check_own_private_file(doc, "handover_evidence", _("signed handover receipt"))
	if frappe.session.user == doc.handover_entered_by:
		frappe.throw(
			_("A second person confirms the handover: {0} entered it and cannot confirm it").format(
				doc.handover_entered_by
			),
			frappe.PermissionError,
			title=_("Second person needed"),
		)
	doc.handover_confirmed_by = frappe.session.user
	doc.handover_confirmed_on = now_datetime()
	doc.flags.confirming = True
	doc.save(ignore_permissions=True)  # the General Manager's confirmation is the authority
	return {"status": doc.status, "days_overdue": doc.days_overdue}


def refresh_title_states():
	"""Daily: keep Due Soon / Overdue and the days past the deadline current (SAL-18 alert)."""
	names = frappe.get_all(
		DOCTYPE, filters={"status": ("not in", (HANDED_OVER, HANDED_OVER_LATE))}, pluck="name"
	)
	for name in names:
		doc = frappe.get_doc(DOCTYPE, name)
		old = (doc.status, doc.days_overdue)
		doc.set_state()
		if (doc.status, doc.days_overdue) != old:
			frappe.db.set_value(
				DOCTYPE, name, {"status": doc.status, "days_overdue": doc.days_overdue}, update_modified=False
			)
