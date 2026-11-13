# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Sale Contract (SAL-06, SAL-13, INS-02, INS-14, INS-20; SRS v2.0 §2.3, §3.3, §6).

P0 behaviour:
- First save freezes the profile's terms into `terms_snapshot`; neither the profile link
  nor the snapshot can change afterwards. No per-contract overrides (SRS v2.0 §1.5).
- Submit generates the installment schedule and marks the units Under Contract.
  It creates no invoice, payment or ledger entry (SRS v2.0 §3.4).
- A profile on legal hold (Profile B) can be drafted but not submitted.
- Cancelling a submitted contract is refused until the cancellation workflow exists.
- The profile's clauses are frozen with the terms (SAL-20, INS-21).
- Submit means signed and notarised: it needs a private signed copy, notary name and
  reference, one Seller, a Seller Guarantor with pledged property, two Witnesses with
  phones, and approved wording for every clause (SAL-19; issue #8).

Review fixes (develop @ cbce4f3):
- Signed copy: the File must be attached to this contract's `signed_copy` field, private,
  on disk, readable by the submitting user, and not shared with any other record.
- Units are locked in ascending name order (services/units.py lock order).
- Notary reference: whitespace removed; `notary_reference_key` is set only at submit
  and carries a database unique index, so two signed contracts can never share one,
  even when submitted at the same moment. Drafts may share a reference.
- Clause approval is checked against the clause library at submit: approving a clause
  later unblocks an existing draft, but only if its wording is unchanged since the
  draft froze it. Changed wording needs a revised draft (`revise_draft`). The signed
  snapshot never changes. Policy in docs/CONTRACT-REVISION_v0.1.md, issue #11.

Contract capture (docs/CONTRACT-CAPTURE_v0.3.md, decisions D1-D7 in issue #13; CC-01 to CC-10):
- `source` "External (registered)" (the default) registers a contract prepared outside the
  system: its own terms and its actual schedule are entered, a profile only pre-fills, and the
  attached original governs. "Generated from profile" keeps every rule above unchanged.
- External drafts keep their schedule rows: nothing regenerates them. `propose_schedule` fills
  rows only when asked, and replaces existing rows only with `replace=1`.
- The schedule reconciles with the amount due (D1 down payment mode, D2 fee rows count); a
  difference up to the Contract Settings tolerance (D3, $5.00) can be confirmed and is stored.
- Confirmation of an External contract needs the original signed contract and a unique
  external reference; signing data is validated only where present (D5).
- Penalty, default and title terms are recorded only, never applied (D6). Confirmation
  records who approved the terms and when (D7) in the contract and in its snapshot.
"""

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime

from sidra_realestate.services.schedule import ScheduleError, down_payment_amount, generate_installments
from sidra_realestate.services.units import UnitNotAvailable, lock_units, set_unit_status
from sidra_realestate.sidra_installments.doctype.sidra_contract_profile.sidra_contract_profile import (
	PENALTY_AND_TITLE_FIELDS,
	check_range,
	validate_penalty_and_title_terms,
)
from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	schedule_tolerance,
)
from sidra_realestate.sidra_sales.doctype.sidra_customer_kyc.sidra_customer_kyc import has_verified_kyc

NOTARY_REFERENCE = re.compile(r"^IPN/HL/\d{3}/\d{4}$")  # SAL-19

EXTERNAL = "External (registered)"
GENERATED = "Generated from profile"
ROW_TYPES = ("Installment", "Down payment", "Fee")
INCLUDED = "Included in schedule"
SEPARATE = "Recorded separately"


class SidraSaleContract(Document):
	def validate(self):
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.validate_units()
		self.validate_price_allocation()
		self.validate_notary_reference()
		self.validate_parties()
		if self.contract_type == "Installment":
			self.source = self.source or EXTERNAL
			if self.is_external():
				self.validate_external_draft()
			else:
				self.freeze_terms()
				self.set_plan_from_terms()
				self.set_captured_terms_from_snapshot()
		else:
			self.validate_cash_contract()
		if self.docstatus == 0:
			if not self.is_external():
				self.set("schedule", [])  # generated at submit only
			self.notary_reference_key = None  # set at submit only
			self.external_reference_key = None  # set at confirmation only
		if self.is_external():
			self.set_schedule_totals(notify=self.docstatus == 0)

	def is_external(self):
		return self.contract_type == "Installment" and self.source == EXTERNAL

	# ------------------------------------------------------------ units and price
	def validate_units(self):
		if not self.units:
			frappe.throw(_("Add at least one unit"))
		seen = set()
		for row in self.units:
			if row.unit in seen:
				frappe.throw(_("Unit {0} is listed twice").format(row.unit))
			seen.add(row.unit)
			unit = frappe.db.get_value(
				"Sidra Unit", row.unit, ["company", "status", "current_reservation"], as_dict=True
			)
			if not unit:
				frappe.throw(_("Unknown unit {0}").format(row.unit), frappe.DoesNotExistError)
			if unit.company != self.company:
				frappe.throw(
					_("Unit {0} belongs to {1}, not {2}").format(row.unit, unit.company, self.company)
				)
			if self.docstatus == 0:
				self.check_unit_available(row.unit, unit)

	def check_unit_available(self, unit_name, unit):
		if unit.status == "Available":
			return
		if unit.status == "Reserved":
			holder = frappe.db.get_value("Sidra Reservation", unit.current_reservation, "customer")
			if holder == self.customer:
				return
			frappe.throw(_("Unit {0} is reserved for another customer").format(unit_name), UnitNotAvailable)
		frappe.throw(_("Unit {0} is {1}").format(unit_name, unit.status), UnitNotAvailable)

	def validate_price_allocation(self):
		if flt(self.agreed_price, 2) <= 0:
			frappe.throw(_("The agreed price must be greater than zero"))
		for row in self.units:
			if flt(row.allocated_price, 2) <= 0:
				frappe.throw(_("Row {0}: the allocated price must be greater than zero").format(row.idx))
		total = flt(sum(flt(row.allocated_price, 2) for row in self.units), 2)
		if total != flt(self.agreed_price, 2):
			frappe.throw(
				_("Unit prices add up to {0} but the agreed price is {1}").format(
					total, flt(self.agreed_price, 2)
				)
			)

	def validate_notary_reference(self):
		self.notary_reference = normalize_notary_reference(self.notary_reference)
		if self.notary_reference and not NOTARY_REFERENCE.match(self.notary_reference):
			frappe.throw(_("Notary reference must look like IPN/HL/NNN/YYYY"))

	# ------------------------------------------------------------ terms
	def freeze_terms(self):
		if not self.contract_profile:
			frappe.throw(_("Choose a contract profile"))
		before = self.get_doc_before_save()
		if before is None:
			profile = frappe.get_doc("Sidra Contract Profile", self.contract_profile)
			if not profile.active:
				frappe.throw(_("Profile {0} is retired").format(profile.name))
			self.terms_snapshot = json.dumps(profile.terms(), sort_keys=True, default=str)
			self.freeze_clauses(profile)
			return
		if (
			before.contract_profile != self.contract_profile
			or _parse(before.terms_snapshot) != _parse(self.terms_snapshot)
			or _clause_rows(before.clauses) != _clause_rows(self.clauses)
		):
			frappe.throw(_("The profile, frozen terms and clauses of a saved contract cannot be changed"))

	def freeze_clauses(self, profile):
		self.set("clauses", [])
		for row in profile.clauses:
			clause = frappe.get_doc("Sidra Contract Clause", row.clause)
			if not clause.active:
				frappe.throw(_("Clause {0} on profile {1} is inactive").format(clause.name, profile.name))
			self.append(
				"clauses",
				{
					"clause": clause.name,
					"title": clause.title,
					"text_so": clause.text_so,
					"text_en": clause.text_en,
					"approved": clause.approved,
				},
			)

	def terms(self) -> dict:
		return _parse(self.terms_snapshot)

	def set_plan_from_terms(self):
		terms = self.terms()
		if flt(terms.get("markup_rate")):
			frappe.throw(_("P0 supports zero-markup profiles only (INS-01 is planned for P2)"))
		try:
			down = down_payment_amount(
				flt(self.agreed_price, 2), terms["down_payment_type"], flt(terms.get("down_payment_value"), 2)
			)
		except ScheduleError as e:
			frappe.throw(str(e))
		self.down_payment = flt(down, 2)
		self.balance = flt(self.agreed_price, 2) - self.down_payment
		self.installments = terms["installments"]
		self.due_day = terms["due_day"]
		self.grace_months = terms["grace_months"]

	def set_captured_terms_from_snapshot(self):
		"""Generated contracts show the profile's frozen penalty and title terms (D6), read-only."""
		terms = self.terms()
		for field in PENALTY_AND_TITLE_FIELDS:
			self.set(field, terms.get(field))
		self.down_payment_mode = SEPARATE if flt(self.down_payment) else "None"

	# ------------------------------------------------------------ external (registered) contracts
	def validate_external_draft(self):
		"""CC-01 to CC-07: captured terms and the actual schedule; nothing is regenerated."""
		self.terms_snapshot = None if self.docstatus == 0 else self.terms_snapshot
		self.set("clauses", [])  # the attached original governs; profile clauses are not frozen
		self.prefill_from_profile()
		self.external_reference = normalize_external_reference(self.external_reference)
		check_range(self, "installments", 0, 60)
		check_range(self, "due_day", 0, 28)
		check_range(self, "grace_months", 0, 12)
		validate_penalty_and_title_terms(self)
		self.validate_schedule_rows()
		self.set_down_payment()

	def prefill_from_profile(self):
		"""A profile chosen on an External contract fills blank captured values only (CC-03)."""
		before = self.get_doc_before_save()
		if not self.contract_profile or (before and before.contract_profile == self.contract_profile):
			return
		profile = frappe.get_doc("Sidra Contract Profile", self.contract_profile)
		if not profile.active:
			frappe.throw(_("Profile {0} is retired").format(profile.name))
		for field in (*PENALTY_AND_TITLE_FIELDS, "installments", "due_day", "grace_months"):
			if not self.get(field):
				self.set(field, profile.get(field))
		if (self.down_payment_mode or "None") == "None" and profile.down_payment_type != "None":
			try:
				down = down_payment_amount(
					flt(self.agreed_price, 2), profile.down_payment_type, flt(profile.down_payment_value, 2)
				)
			except ScheduleError as e:
				frappe.throw(str(e))
			self.down_payment_mode = SEPARATE
			self.down_payment = flt(down, 2)

	def validate_schedule_rows(self):
		for seq, row in enumerate(self.schedule, start=1):
			row.seq = seq
			row.row_type = row.row_type or "Installment"
			if row.row_type not in ROW_TYPES:
				frappe.throw(_("Schedule row {0}: unknown type {1}").format(seq, row.row_type))
			if not row.due_date:
				frappe.throw(_("Schedule row {0}: enter the due date").format(seq))
			row.amount = flt(row.amount, 2)
			if row.amount <= 0:
				frappe.throw(_("Schedule row {0}: the amount must be greater than zero").format(seq))

	def set_down_payment(self):
		"""Decision D1: the down payment is in the schedule, recorded separately, or there is none."""
		mode = self.down_payment_mode = self.down_payment_mode or "None"
		down_rows = [row for row in self.schedule if row.row_type == "Down payment"]
		if mode == INCLUDED:
			self.down_payment = flt(sum(row.amount for row in down_rows), 2)
		elif down_rows:
			frappe.throw(
				_("Down payment rows need the down payment mode '{0}', not '{1}'").format(
					_(INCLUDED), _(mode)
				)
			)
		elif mode == SEPARATE:
			self.down_payment = flt(self.down_payment, 2)
			if self.down_payment < 0 or self.down_payment > flt(self.agreed_price, 2):
				frappe.throw(_("The down payment must be from zero to the agreed price"))
		else:
			self.down_payment = 0
		self.balance = flt(self.agreed_price, 2) - flt(self.down_payment, 2)

	def set_schedule_totals(self, notify=False):
		"""CC-07: schedule total, amount due and the difference, recomputed on every save (D1, D2)."""
		self.schedule_total = flt(sum(flt(row.amount, 2) for row in self.schedule), 2)
		self.amount_due = flt(self.agreed_price, 2)
		if self.down_payment_mode == SEPARATE:
			self.amount_due = flt(self.amount_due - flt(self.down_payment, 2), 2)
		self.schedule_difference = flt(self.amount_due - self.schedule_total, 2)
		if notify and self.schedule and self.schedule_difference:
			limit = schedule_tolerance()
			within = abs(self.schedule_difference) <= limit
			frappe.msgprint(
				_("The schedule differs from the amount due by {0}; the limit is {1}. {2}").format(
					self.schedule_difference,
					limit,
					_("It can be confirmed after acknowledgement.")
					if within
					else _("It cannot be confirmed until it reconciles."),
				),
				indicator="orange" if within else "red",
				alert=True,
			)

	def check_external_confirmation(self):
		"""Confirmation of a registered contract (brief §6.2 step 5, b to f)."""
		if not self.signed_copy:
			frappe.throw(
				_("Attach the original signed contract before confirming"), title=_("Not signed yet")
			)
		self.check_signed_copy()
		for row in self.parties:
			if not row.full_name:
				frappe.throw(_("Parties row {0}: enter the name").format(row.idx))
			if row.role == "Seller Guarantor" and not (row.pledged_property or "").strip():
				frappe.throw(_("Parties row {0}: enter the guarantor's pledged property").format(row.idx))
		if self.notary_reference:
			self.reserve_notary_reference()
		self.reserve_external_reference()

		mode = self.down_payment_mode
		if mode == INCLUDED and not any(row.row_type == "Down payment" for row in self.schedule):
			frappe.throw(_("Add the Down payment row(s), or change the down payment mode"))
		if mode == SEPARATE and flt(self.down_payment, 2) <= 0:
			frappe.throw(_("Enter the down payment recorded separately, or change the down payment mode"))
		if not self.schedule:
			frappe.throw(_("Enter the schedule: at least one row"))
		self._tolerance = schedule_tolerance()
		if abs(flt(self.schedule_difference, 2)) > self._tolerance:
			frappe.throw(
				_("The schedule differs from the amount due by {0}, more than the limit of {1}").format(
					self.schedule_difference, self._tolerance
				),
				title=_("Schedule does not reconcile"),
			)

	def reserve_external_reference(self):
		"""Unique per Company among confirmed contracts; the unique index decides any race."""
		if not self.external_reference:
			frappe.throw(_("Enter the external reference (the contract's own number) before confirming"))
		key = f"{self.company}::{self.external_reference}"
		duplicate = frappe.db.get_value(
			"Sidra Sale Contract", {"external_reference_key": key, "name": ("!=", self.name)}, "name"
		)
		if duplicate:
			frappe.throw(
				_("External reference {0} is already used by {1}").format(self.external_reference, duplicate)
			)
		self.external_reference_key = key

	def record_confirmation(self):
		"""D7 approval record, and the frozen snapshot of what was confirmed (INS-20)."""
		self.terms_approved_by = frappe.session.user
		self.terms_approved_on = now_datetime()
		approval = {
			"terms_approved_by": self.terms_approved_by,
			"terms_approved_on": str(self.terms_approved_on),
		}
		if self.is_external():
			terms = {
				field: self.get(field)
				for field in (
					"source",
					"external_reference",
					"contract_profile",
					"down_payment_mode",
					"down_payment",
					"terms_summary",
					"installments",
					"due_day",
					"grace_months",
					"schedule_total",
					"amount_due",
					"schedule_difference",
					*PENALTY_AND_TITLE_FIELDS,
				)
			}
			terms["schedule_tolerance"] = self._tolerance
		else:
			terms = {**self.terms(), "source": self.source}
		self.terms_snapshot = json.dumps({**terms, **approval}, sort_keys=True, default=str)

	def validate_cash_contract(self):
		if self.contract_profile or self.terms_snapshot or self.clauses:
			frappe.throw(_("A cash contract has no contract profile or profile clauses (issue #8)"))
		self.source = None
		self.external_reference = None
		self.down_payment = 0
		self.balance = 0
		self.installments = self.due_day = self.grace_months = 0

	def validate_parties(self):
		for row in self.parties:
			row.full_name = (row.full_name or "").strip()
			if row.role != "Seller Guarantor" and row.pledged_property:
				frappe.throw(_("Parties row {0}: only a Seller Guarantor pledges property").format(row.idx))

	# ------------------------------------------------------------ submit
	def check_signing_gate(self):
		"""Submit means signed and notarised (SAL-19; SRS v2.0 §9 item 6; issue #8)."""
		missing = []
		if not self.signed_copy:
			missing.append(_("the signed copy"))
		else:
			self.check_signed_copy()
		if not has_verified_kyc(self.customer):
			missing.append(_("the buyer's verified KYC"))  # SAL-07, G12: generated contracts only
		if not (self.notary_name or "").strip():
			missing.append(_("the notary"))
		if not (self.notary_reference or "").strip():
			missing.append(_("the notary reference"))

		roles = [row.role for row in self.parties]
		if roles.count("Seller") != 1:
			missing.append(_("exactly one Seller"))
		guarantors = [row for row in self.parties if row.role == "Seller Guarantor"]
		if not guarantors or any(not (row.pledged_property or "").strip() for row in guarantors):
			missing.append(_("a Seller Guarantor with the pledged property"))
		witnesses = [row for row in self.parties if row.role == "Witness"]
		if len(witnesses) < 2 or any(not (row.phone or "").strip() for row in witnesses):
			missing.append(_("two Witnesses with phone numbers"))

		unapproved, changed = self.clause_approval_problems()
		if unapproved:
			missing.append(_("approved wording for clause(s) {0}").format(", ".join(unapproved)))

		if missing:
			frappe.throw(
				_("Before submitting, add: {0}").format("; ".join(missing)), title=_("Not signed yet")
			)
		if changed:
			frappe.throw(
				_(
					"The approved wording of clause(s) {0} differs from the wording frozen in this draft. "
					"Use Revise Draft to make a new draft with the current wording."
				).format(", ".join(changed)),
				title=_("Clause wording changed"),
			)

	def check_signed_copy(self):
		"""Review finding 1: the signed scan must belong to this contract and nobody else."""
		files = frappe.get_all(
			"File",
			filters={"file_url": self.signed_copy},
			fields=["name", "is_private", "attached_to_doctype", "attached_to_name", "attached_to_field"],
		)
		own = [
			f
			for f in files
			if (f.attached_to_doctype, f.attached_to_name, f.attached_to_field)
			== (self.doctype, self.name, "signed_copy")
		]
		if not own:
			frappe.throw(
				_("Upload the signed copy to this contract's Signed Copy field and save before submitting"),
				title=_("Signed copy not attached"),
			)
		if len(own) != len(files):
			frappe.throw(
				_("This signed copy file is also used by another record; upload this contract's own scan"),
				frappe.PermissionError,
			)
		file_doc = frappe.get_doc("File", own[0].name)
		if not file_doc.is_private:
			frappe.throw(_("The signed copy must be a private file"))
		if not file_doc.has_permission("read"):
			frappe.throw(_("You cannot read this signed copy"), frappe.PermissionError)
		if not file_doc.exists_on_disk():
			frappe.throw(_("The signed copy file is missing from the server; upload it again"))

	def clause_approval_problems(self):
		"""Check each frozen clause against the library now (review finding 5).

		Returns (not approved, approved but with different wording)."""
		unapproved, changed = [], []
		for row in self.clauses:
			lib = frappe.db.get_value(
				"Sidra Contract Clause", row.clause, ["approved", "text_so", "text_en"], as_dict=True
			)
			if not lib or not lib.approved:
				unapproved.append(row.clause)
			elif (lib.text_so or "", lib.text_en or "") != (row.text_so or "", row.text_en or ""):
				changed.append(row.clause)
		return unapproved, changed

	def reserve_notary_reference(self):
		"""Fill the unique key (review finding 3). The database index decides any race."""
		duplicate = frappe.db.get_value(
			"Sidra Sale Contract",
			{"notary_reference_key": self.notary_reference, "name": ("!=", self.name)},
			"name",
		)
		if duplicate:
			frappe.throw(
				_("Notary reference {0} is already used by {1}").format(self.notary_reference, duplicate)
			)
		self.notary_reference_key = self.notary_reference

	def before_submit(self):
		if self.contract_type == "Installment" and self.contract_profile:
			self.check_legal_hold()  # first: a held profile must not be signed at all
		if self.is_external():
			self.check_external_confirmation()
		else:
			self.check_signing_gate()
			self.reserve_notary_reference()
		for row in self.clauses:
			row.approved = 1  # approval as checked at signing; frozen from here on
		self.lock_units()
		if self.contract_type == "Installment" and not self.is_external():
			self.make_schedule()
			self.schedule_total = flt(sum(flt(row.amount, 2) for row in self.schedule), 2)
			self.amount_due = self.balance
			self.schedule_difference = flt(self.amount_due - self.schedule_total, 2)
		if self.contract_type == "Installment":
			self.record_confirmation()
		else:
			self.terms_approved_by = frappe.session.user
			self.terms_approved_on = now_datetime()

	def check_legal_hold(self):
		live_hold = frappe.db.get_value("Sidra Contract Profile", self.contract_profile, "legal_hold")
		if live_hold or self.terms().get("legal_hold"):
			frappe.throw(
				_("Profile {0} is on legal hold: contracts can be drafted but not submitted").format(
					self.contract_profile
				)
			)

	def lock_units(self):
		self._locked_units = lock_units(row.unit for row in self.units)
		for unit in self._locked_units:
			self.check_unit_available(unit.name, unit)

	def make_schedule(self):
		try:
			lines = generate_installments(
				flt(self.agreed_price, 2),
				flt(self.down_payment, 2),
				self.installments,
				getdate(self.signed_on),
				self.grace_months,
				self.due_day,
			)
		except ScheduleError as e:
			frappe.throw(str(e))
		self.set("schedule", [])
		for line in lines:
			self.append(
				"schedule",
				{
					"seq": line.seq,
					"row_type": "Installment",
					"due_date": line.due_date,
					"amount": flt(line.amount, 2),
				},
			)

	def on_submit(self):
		for unit in self._locked_units:
			reservation = unit.current_reservation
			set_unit_status(unit, "Under Contract", current_contract=self.name, current_reservation=None)
			if reservation:
				doc = frappe.get_doc("Sidra Reservation", reservation, for_update=True)
				doc.status = "Converted"
				doc.sale_contract = self.name
				doc.flags.via_service = True
				doc.save(ignore_permissions=True)

	def before_cancel(self):
		frappe.throw(
			_(
				"A submitted contract cannot be cancelled in this version; cancellation and refund "
				"need the approved workflow (SAL-09, INS-16)"
			)
		)


def normalize_external_reference(value):
	"""Trim, collapse inner spaces and upper-case: ' ext-demo  0001 ' -> 'EXT-DEMO 0001'."""
	return re.sub(r"\s+", " ", (value or "").strip()).upper() or None


@frappe.whitelist(methods=["POST"])
def propose_schedule(contract: str, replace: int = 0, down_payment: float | None = None) -> int:
	"""CC-06: fill an External draft's schedule from its captured terms, only when asked.

	Existing rows are replaced only with `replace=1`. The rows stay editable afterwards and
	are never regenerated on save or confirmation. Returns the number of rows.
	"""
	doc = frappe.get_doc("Sidra Sale Contract", contract)
	doc.check_permission("write")
	if doc.docstatus != 0 or not doc.is_external():
		frappe.throw(_("Only a draft External contract can have its schedule proposed"))
	if doc.schedule and not cint(replace):
		frappe.throw(
			_("The schedule already has {0} rows; confirm to replace them").format(len(doc.schedule))
		)
	if not doc.installments or not doc.due_day:
		frappe.throw(_("Enter the number of installments and the due day first"))

	mode = doc.down_payment_mode or "None"
	if mode == INCLUDED:
		down = flt(doc.down_payment if down_payment is None else down_payment, 2)
		if down <= 0:
			frappe.throw(_("Enter the down payment amount to include in the schedule"))
	elif mode == SEPARATE:
		down = flt(doc.down_payment, 2)
	else:
		down = 0
	try:
		lines = generate_installments(
			flt(doc.agreed_price, 2),
			down,
			cint(doc.installments),
			getdate(doc.signed_on),
			cint(doc.grace_months),
			cint(doc.due_day),
		)
	except ScheduleError as e:
		frappe.throw(str(e))

	doc.set("schedule", [])
	if mode == INCLUDED:
		doc.append("schedule", {"row_type": "Down payment", "due_date": doc.signed_on, "amount": down})
	for line in lines:
		doc.append(
			"schedule", {"row_type": "Installment", "due_date": line.due_date, "amount": flt(line.amount, 2)}
		)
	doc.save()
	return len(doc.schedule)


def normalize_notary_reference(value):
	"""Remove all whitespace: ' IPN/HL/ 042 /2026 ' -> 'IPN/HL/042/2026'."""
	return re.sub(r"\s+", "", value or "") or None


@frappe.whitelist(methods=["POST"])
def revise_draft(contract: str) -> str:
	"""Make a new draft from a draft, with the profile's current terms and clause wording.

	The old draft is left unchanged with a comment pointing to its revision. The signed
	copy is not carried over: a revision is signed afresh. See docs/CONTRACT-REVISION_v0.1.md.
	"""
	old = frappe.get_doc("Sidra Sale Contract", contract)
	old.check_permission("write")
	if old.docstatus != 0:
		frappe.throw(_("Only a draft can be revised; a signed contract keeps its terms"))
	if old.is_external():
		frappe.throw(
			_("A registered External contract is edited directly; Revise Draft is for generated contracts")
		)

	new = frappe.copy_doc(old)
	new.terms_snapshot = None
	new.signed_copy = None
	new.notary_reference_key = None
	new.set("clauses", [])
	new.set("schedule", [])
	new.insert()

	old.add_comment("Info", _("Superseded by revised draft {0}").format(new.name))
	new.add_comment("Info", _("Revision of draft {0}").format(old.name))
	return new.name


def _clause_rows(rows):
	return [
		(row.clause, row.title, row.text_so or "", row.text_en or "", int(row.approved or 0))
		for row in rows or []
	]


def _parse(value):
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	return json.loads(value)
