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
"""

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from sidra_realestate.services.schedule import ScheduleError, down_payment_amount, generate_installments
from sidra_realestate.services.units import UnitNotAvailable, lock_units, set_unit_status

NOTARY_REFERENCE = re.compile(r"^IPN/HL/\d{3}/\d{4}$")  # SAL-19


class SidraSaleContract(Document):
	def validate(self):
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.validate_units()
		self.validate_price_allocation()
		self.validate_notary_reference()
		self.validate_parties()
		if self.contract_type == "Installment":
			self.freeze_terms()
			self.set_plan_from_terms()
		else:
			self.validate_cash_contract()
		if self.docstatus == 0:
			self.set("schedule", [])  # generated at submit only
			self.notary_reference_key = None  # set at submit only

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
				frappe.throw(_("Unit {0} belongs to {1}, not {2}").format(row.unit, unit.company, self.company))
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
				_("Unit prices add up to {0} but the agreed price is {1}").format(total, flt(self.agreed_price, 2))
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

	def validate_cash_contract(self):
		if self.contract_profile or self.terms_snapshot or self.clauses:
			frappe.throw(_("A cash contract has no contract profile or profile clauses (issue #8)"))
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
			frappe.throw(_("Before submitting, add: {0}").format("; ".join(missing)), title=_("Not signed yet"))
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
			frappe.throw(_("Notary reference {0} is already used by {1}").format(self.notary_reference, duplicate))
		self.notary_reference_key = self.notary_reference

	def before_submit(self):
		if self.contract_type == "Installment":
			self.check_legal_hold()  # first: a held profile must not be signed at all
		self.check_signing_gate()
		self.reserve_notary_reference()
		for row in self.clauses:
			row.approved = 1  # approval as checked at signing; frozen from here on
		self.lock_units()
		if self.contract_type == "Installment":
			self.make_schedule()

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
			self.append("schedule", {"seq": line.seq, "due_date": line.due_date, "amount": flt(line.amount, 2)})

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
		(row.clause, row.title, row.text_so or "", row.text_en or "", int(row.approved or 0)) for row in rows or []
	]


def _parse(value):
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	return json.loads(value)
