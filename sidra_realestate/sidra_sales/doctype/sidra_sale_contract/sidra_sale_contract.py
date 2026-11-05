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
"""

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from sidra_realestate.services.schedule import ScheduleError, down_payment_amount, generate_installments
from sidra_realestate.services.units import UnitNotAvailable, lock_unit, set_unit_status

NOTARY_REFERENCE = re.compile(r"^IPN/HL/\d{3}/\d{4}$")  # SAL-19


class SidraSaleContract(Document):
	def validate(self):
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
		if self.notary_reference and not NOTARY_REFERENCE.match(self.notary_reference.strip()):
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
		elif not frappe.db.get_value("File", {"file_url": self.signed_copy}, "is_private"):
			missing.append(_("the signed copy as a private file"))
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

		unapproved = [row.clause for row in self.clauses if not row.approved]
		if unapproved:
			missing.append(_("approved wording for clause(s) {0}").format(", ".join(unapproved)))

		if missing:
			frappe.throw(_("Before submitting, add: {0}").format("; ".join(missing)), title=_("Not signed yet"))

		duplicate = frappe.db.exists(
			"Sidra Sale Contract",
			{"notary_reference": self.notary_reference.strip(), "docstatus": 1, "name": ("!=", self.name)},
		)
		if duplicate:
			frappe.throw(_("Notary reference {0} is already used by {1}").format(self.notary_reference, duplicate))

	def before_submit(self):
		self.check_signing_gate()
		if self.contract_type == "Installment":
			self.check_legal_hold()
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
		self._locked_units = []
		for row in self.units:
			unit = lock_unit(row.unit)
			self.check_unit_available(row.unit, unit)
			self._locked_units.append(unit)

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
