# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Workflow timeline for one transaction: read-only, derived from saved records on every call.

`get_contract_timeline(contract)` returns the ordered stages of registering an External
contract (docs/CONTRACT-CAPTURE_v0.3.md §6.2) for the workflow panel of the new interface.

- Nothing is stored: no status field, no cache, no write. Each state is worked out from the
  contract, its units, its signed-copy File, the buyer's KYC record and Contract Settings.
- Exactly one stage is `current` or `blocked`; the stages after it are `pending`. When every
  stage holds, all are `completed`.
- The caller needs read permission on the contract (PermissionError otherwise). Evidence held
  in a record the caller cannot read is returned as unavailable, never guessed, never zero.
- `allowed_actions` names what the CURRENT user may do next. This module performs none of
  them: transitions stay in the DocType controllers and their own whitelisted methods.

Stage evidence (approved by Mohamoud, 13 Nov 2026):
1. Buyer details verified - Sidra Customer KYC `status = Verified`. Informational for
   registered contracts: decision G12 does not require KYC for them, so it never blocks.
2. Property allocation checked - re-derived: units listed, same Company, each Available or
   reserved for this buyer, unit prices add up to the agreed price. After confirmation the
   units are Under Contract and point at this contract.
3. External agreement attached - `signed_copy` and its own private File on that field.
4. Installment schedule validated - rows, down payment mode (D1) and the difference between
   the schedule total and the amount due against the tolerance (D3).
5. Terms approval (Sales Manager) - decision D7: `terms_approved_by`, `terms_approved_on`.
   There is no separate Finance approval in the system.
6. Registration finalized - the contract is submitted and its external reference is reserved.

To add a process (collections, construction): add its stages to `PROCESSES` and say in
`process_for` which documents it covers.
"""

from dataclasses import dataclass, field

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, get_fullname

from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	schedule_tolerance,
)
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import (
	INCLUDED,
	SEPARATE,
)

COMPLETED, CURRENT, BLOCKED, PENDING = "completed", "current", "blocked", "pending"
STATES = (COMPLETED, CURRENT, BLOCKED, PENDING)
UNAVAILABLE = "unavailable"

EXTERNAL_REGISTRATION = "external_contract_registration"
APPROVER_ROLE = "Sidra Sales Manager"  # decision D7
MONEY_FIELDS = ("agreed_price", "down_payment", "schedule_total", "amount_due", "schedule_difference")

OK, WAITING, STOPPED = "ok", "waiting", "stopped"


@dataclass
class Check:
	"""What the saved records say about one stage, before the stages are put in order."""

	status: str = OK  # OK | WAITING (someone has to act) | STOPPED (a rule refuses)
	detail: str | None = None  # plain words for the panel
	reason: str | None = None  # why it is stopped
	action_key: str | None = None  # the action that moves a waiting or stopped stage on
	actions: tuple = ()  # candidate actions, filtered by the user's permissions
	responsible: str | None = None
	timestamp: object = None
	record: dict | None = None
	figures: dict | None = None
	skipped: bool = False  # not required for this transaction and not evidenced
	unavailable: bool = False  # the evidence is in a record this user cannot read
	extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------- stage checks
def check_buyer(doc):
	"""Stage 1. Informational for registered contracts (G12): never waiting, never stopped."""
	not_required = _("Not required for registered contracts.")
	if not frappe.has_permission("Sidra Customer KYC", "read"):
		return Check(unavailable=True, detail=_("Buyer KYC is restricted; its state is unavailable to you."))
	kyc = frappe.db.get_value(
		"Sidra Customer KYC",
		{"customer": doc.customer},
		["name", "status", "verified_by", "verified_on"],
		as_dict=True,
	)
	if not kyc:
		return Check(
			skipped=True,
			detail=_("{0} No buyer KYC is on record.").format(not_required),
			actions=("create_kyc",),
		)
	if not frappe.has_permission("Sidra Customer KYC", "read", doc=kyc.name):
		return Check(unavailable=True, detail=_("Buyer KYC is restricted; its state is unavailable to you."))
	record = {"doctype": "Sidra Customer KYC", "name": kyc.name}
	if kyc.status != "Verified":
		return Check(
			skipped=True,
			detail=_("{0} Buyer KYC is entered but not verified.").format(not_required),
			record=record,
			actions=("verify_kyc",),
			extra={"kyc": kyc.name},
		)
	return Check(
		detail=_("Buyer KYC verified."),
		responsible=_person(kyc.verified_by),
		timestamp=kyc.verified_on,
		record=record,
	)


def check_allocation(doc):
	"""Stage 2. No one records a check, so it is derived again from the units on every call."""
	edit = {"action_key": "edit_contract", "actions": ("edit_contract",)}
	if not doc.units:
		return Check(status=WAITING, detail=_("Add at least one unit."), **edit)
	units = {
		row.unit: frappe.db.get_value(
			"Sidra Unit",
			row.unit,
			["company", "status", "current_reservation", "current_contract"],
			as_dict=True,
		)
		for row in doc.units
	}
	record = _unit_record(doc)

	if doc.docstatus == 1:
		# Checked and locked by the server at confirmation; a later change is reported, not judged.
		moved = [
			_("Unit {0} is now {1}").format(name, unit.status if unit else _("missing"))
			for name, unit in units.items()
			if not unit or unit.current_contract != doc.name or unit.status != "Under Contract"
		]
		return Check(
			detail="; ".join(moved) if moved else _("Units are under this contract."),
			responsible=_("System"),
			timestamp=doc.terms_approved_on,
			record=record,
		)

	problems = []
	for name, unit in units.items():
		if not unit:
			problems.append(_("Unit {0} no longer exists").format(name))
		elif unit.company != doc.company:
			problems.append(_("Unit {0} belongs to {1}, not {2}").format(name, unit.company, doc.company))
		elif unit.status == "Reserved":
			holder = frappe.db.get_value("Sidra Reservation", unit.current_reservation, "customer")
			if holder != doc.customer:
				problems.append(_("Unit {0} is reserved for another customer").format(name))
		elif unit.status != "Available":
			problems.append(_("Unit {0} is {1}").format(name, unit.status))
	allocated = flt(sum(flt(row.allocated_price, 2) for row in doc.units), 2)
	if allocated != flt(doc.agreed_price, 2):
		if _can_see_money(doc):
			problems.append(
				_("Unit prices add up to {0} but the agreed price is {1}").format(
					_money(doc, allocated), _money(doc, doc.agreed_price)
				)
			)
		else:
			problems.append(_("Unit prices do not add up to the agreed price"))
	if problems:
		return Check(status=STOPPED, reason="; ".join(problems), record=record, **edit)
	return Check(
		detail=_("Checked by the system against the saved units."),
		responsible=_("System"),
		timestamp=doc.modified,
		record=record,
	)


def check_agreement(doc):
	"""Stage 3. The original signed contract, as its own private File on the Signed Copy field."""
	attach = {"action_key": "attach_agreement", "actions": ("attach_agreement",)}
	if not doc.signed_copy:
		return Check(status=WAITING, detail=_("Attach the original signed contract."), **attach)
	files = frappe.get_all(
		"File",
		filters={"file_url": doc.signed_copy},
		fields=[
			"name",
			"is_private",
			"owner",
			"creation",
			"attached_to_doctype",
			"attached_to_name",
			"attached_to_field",
		],
		order_by="creation asc",
	)
	own = [
		f
		for f in files
		if (f.attached_to_doctype, f.attached_to_name, f.attached_to_field)
		== (doc.doctype, doc.name, "signed_copy")
	]
	if not own:
		reason = _("The signed copy is not attached to this contract's Signed Copy field")
	elif len(own) != len(files):
		reason = _("This signed copy file is also used by another record")
	elif not own[0].is_private:
		reason = _("The signed copy must be a private file")
	else:
		reason = None
	if reason:
		return Check(status=STOPPED, reason=reason, **attach)
	readable = frappe.has_permission("File", "read", doc=own[0].name)
	return Check(
		detail=_("Original signed contract attached."),
		responsible=_person(own[0].owner),
		timestamp=own[0].creation,
		record={"doctype": "File", "name": own[0].name} if readable else None,
	)


def check_schedule(doc):
	"""Stage 4. Rows, down payment mode (D1) and the difference against the tolerance (D3)."""
	edit = {"action_key": "edit_schedule", "actions": ("edit_schedule",)}
	confirmed = doc.docstatus == 1
	total = flt(sum(flt(row.amount, 2) for row in doc.schedule), 2)
	due = flt(doc.agreed_price, 2)
	if doc.down_payment_mode == SEPARATE:
		due = flt(due - flt(doc.down_payment, 2), 2)
	difference = flt(due - total, 2)
	# A confirmed contract keeps the tolerance it was confirmed under (frozen in its snapshot).
	frozen = _snapshot(doc).get("schedule_tolerance") if confirmed else None
	tolerance = flt(schedule_tolerance() if frozen is None else frozen, 2)
	visible = _can_see_money(doc)
	figures = {
		"currency": doc.currency,
		"schedule_total": total if visible else UNAVAILABLE,
		"amount_due": due if visible else UNAVAILABLE,
		"difference": difference if visible else UNAVAILABLE,
		"tolerance": tolerance,
		"rows": len(doc.schedule),
	}

	if not confirmed:
		mode = doc.down_payment_mode or "None"
		if not doc.schedule:
			return Check(
				status=WAITING, detail=_("Enter the schedule: at least one row."), figures=figures, **edit
			)
		if mode == INCLUDED and not any(row.row_type == "Down payment" for row in doc.schedule):
			return Check(
				status=STOPPED,
				reason=_("The down payment is included in the schedule but there is no Down payment row"),
				figures=figures,
				**edit,
			)
		if mode == SEPARATE and flt(doc.down_payment, 2) <= 0:
			return Check(
				status=STOPPED,
				reason=_("The down payment is recorded separately but no amount is entered"),
				figures=figures,
				**edit,
			)
		if abs(difference) > tolerance:
			if visible:
				reason = _(
					"The schedule total {0} differs from the amount due {1} by {2}; the limit is {3}"
				).format(
					_money(doc, total), _money(doc, due), _money(doc, difference), _money(doc, tolerance)
				)
			else:
				reason = _(
					"The schedule total differs from the amount due by more than the limit of {0}"
				).format(_money(doc, tolerance))
			return Check(status=STOPPED, reason=reason, figures=figures, **edit)

	if not difference:
		detail = _("The schedule equals the amount due.")
	elif visible:
		detail = _("The schedule differs from the amount due by {0}, within the limit of {1}.").format(
			_money(doc, difference), _money(doc, tolerance)
		)
	else:
		detail = _("The schedule differs from the amount due, within the limit.")
	return Check(
		detail=detail,
		responsible=_("System"),
		timestamp=doc.terms_approved_on if confirmed else doc.modified,
		record=_contract_record(doc),
		figures=figures,
	)


def check_approval(doc):
	"""Stage 5. Decision D7: the Sales Manager's confirmation is the approval of the terms."""
	if doc.docstatus == 1:
		return Check(
			detail=_("Terms approved at confirmation."),
			responsible=_person(doc.terms_approved_by),
			timestamp=doc.terms_approved_on,
			record=_contract_record(doc),
		)
	edit = {"action_key": "edit_contract", "actions": ("edit_contract",)}
	if doc.contract_profile and frappe.db.get_value(
		"Sidra Contract Profile", doc.contract_profile, "legal_hold"
	):
		return Check(
			status=STOPPED,
			reason=_("Profile {0} is on legal hold: the contract cannot be confirmed").format(
				doc.contract_profile
			),
			action_key="edit_contract",
			actions=("edit_contract",),
		)
	if not doc.external_reference:
		return Check(
			status=STOPPED, reason=_("Enter the external reference (the contract's own number)"), **edit
		)
	duplicate = frappe.db.get_value(
		"Sidra Sale Contract",
		{"external_reference_key": f"{doc.company}::{doc.external_reference}", "name": ("!=", doc.name)},
		"name",
	)
	if duplicate:
		return Check(
			status=STOPPED,
			reason=_("External reference {0} is already used by {1}").format(
				doc.external_reference, duplicate
			),
			**edit,
		)
	for row in doc.parties:
		if not row.full_name:
			return Check(status=STOPPED, reason=_("Parties row {0}: enter the name").format(row.idx), **edit)
		if row.role == "Seller Guarantor" and not (row.pledged_property or "").strip():
			return Check(
				status=STOPPED,
				reason=_("Parties row {0}: enter the guarantor's pledged property").format(row.idx),
				**edit,
			)
	if doc.notary_reference:
		duplicate = frappe.db.get_value(
			"Sidra Sale Contract",
			{"notary_reference_key": doc.notary_reference, "name": ("!=", doc.name)},
			"name",
		)
		if duplicate:
			return Check(
				status=STOPPED,
				reason=_("Notary reference {0} is already used by {1}").format(
					doc.notary_reference, duplicate
				),
				**edit,
			)
	return Check(
		status=WAITING,
		detail=_("Awaiting confirmation by a {0}.").format(_(APPROVER_ROLE)),
		responsible=_(APPROVER_ROLE),
		action_key="confirm_contract",
		actions=("confirm_contract",),
	)


def check_registration(doc):
	"""Stage 6. Submitted, with the external reference reserved for this Company."""
	if doc.docstatus == 1 and doc.external_reference_key:
		return Check(
			detail=_("Registered as {0}.").format(doc.external_reference),
			responsible=_person(doc.terms_approved_by),
			timestamp=doc.terms_approved_on,
			record=_contract_record(doc),
		)
	if doc.docstatus == 2:
		return Check(status=STOPPED, reason=_("The contract is cancelled"))
	return Check(status=WAITING, detail=_("Completes when the contract is confirmed."))


# The one place a process's stages are defined: (key, label, check), in order.
PROCESSES = {
	EXTERNAL_REGISTRATION: (
		("buyer_verified", "Buyer details verified", check_buyer),
		("property_allocation", "Property allocation checked", check_allocation),
		("agreement_attached", "External agreement attached", check_agreement),
		("schedule_validated", "Installment schedule validated", check_schedule),
		("terms_approval", "Terms approval (Sales Manager)", check_approval),
		("registration_finalized", "Registration finalized", check_registration),
	),
}


def process_for(doc):
	"""Which process a document follows; None when no stage list is defined for it yet."""
	if doc.doctype == "Sidra Sale Contract" and doc.is_external():
		return EXTERNAL_REGISTRATION
	return None


# ---------------------------------------------------------------------- the method
@frappe.whitelist(methods=["GET"])
def get_contract_timeline(contract: str) -> dict:
	"""The workflow timeline of one sale contract, for the signed-in user. Reads only."""
	doc = frappe.get_doc("Sidra Sale Contract", contract)
	doc.check_permission("read")
	process = process_for(doc)
	transaction = {
		"doctype": doc.doctype,
		"name": doc.name,
		"process": process,
		"docstatus": doc.docstatus,
		"status": {0: "Draft", 1: "Confirmed", 2: "Cancelled"}[doc.docstatus],
		"contract_type": doc.contract_type,
		"source": doc.source,
		"company": doc.company,
		"customer": doc.customer,
		"external_reference": doc.external_reference,
		"modified": str(doc.modified),
	}
	if not process:
		return {
			"transaction": transaction,
			"supported": False,
			"reason": _("No workflow is defined yet for this kind of contract."),
			"stages": [],
		}
	return {
		"transaction": transaction,
		"supported": True,
		"reason": None,
		"stages": build_stages(doc, process),
	}


def build_stages(doc, process):
	"""Run each stage's check, then order the states: the first stage that does not hold is
	`current` (someone has to act) or `blocked` (a rule refuses); everything after it is `pending`."""
	stages, waiting_on = [], None
	for key, label, check in PROCESSES[process]:
		if waiting_on:
			stages.append(_stage(key, label, PENDING, detail=_("After: {0}").format(_(waiting_on))))
			continue
		found = check(doc)
		if found.status == OK:
			state = COMPLETED
		else:
			state = CURRENT if found.status == WAITING else BLOCKED
			waiting_on = label
		blocker = None
		if state == BLOCKED:
			blocker = {"reason": found.reason, "action_key": found.action_key}
		stages.append(
			_stage(
				key,
				label,
				state,
				detail=found.detail,
				responsible=found.responsible,
				timestamp=str(found.timestamp) if found.timestamp else None,
				record=found.record,
				blocker=blocker,
				next_action=found.action_key if state == CURRENT else None,
				allowed_actions=[a for a in found.actions if _may(a, doc, found)],
				figures=found.figures,
				skipped=found.skipped,
				unavailable=found.unavailable,
			)
		)
	return stages


def _stage(key, label, state, **values):
	stage = {
		"key": key,
		"label": _(label),
		"state": state,
		"detail": None,
		"responsible": None,
		"timestamp": None,
		"record": None,
		"blocker": None,
		"next_action": None,
		"allowed_actions": [],
		"figures": None,
		"skipped": False,
		"unavailable": False,
	}
	stage.update(values)
	return stage


# ---------------------------------------------------------------------- permissions and helpers
def _may(action, doc, found):
	"""Whether the current user may take `action`. The server enforces each again when it is taken."""
	if action in ("edit_contract", "attach_agreement", "edit_schedule"):
		return doc.docstatus == 0 and bool(doc.has_permission("write"))
	if action == "confirm_contract":
		return doc.docstatus == 0 and bool(doc.has_permission("submit"))
	if action == "create_kyc":
		return bool(frappe.has_permission("Sidra Customer KYC", "create"))
	if action == "verify_kyc":
		return APPROVER_ROLE in frappe.get_roles() and bool(
			frappe.has_permission("Sidra Customer KYC", "write", doc=found.extra.get("kyc"))
		)
	return False


def _can_see_money(doc):
	"""No contract amount is restricted today. If one is ever given a higher permission level,
	a user without that level gets `unavailable` here instead of the figure."""
	return all(doc.has_permlevel_access_to(fieldname) for fieldname in MONEY_FIELDS)


def _money(doc, value):
	return fmt_money(flt(value, 2), precision=2, currency=doc.currency)


def _person(user):
	return get_fullname(user) if user else None


def _contract_record(doc):
	return {"doctype": doc.doctype, "name": doc.name}


def _unit_record(doc):
	if len(doc.units) == 1 and frappe.has_permission("Sidra Unit", "read"):
		return {"doctype": "Sidra Unit", "name": doc.units[0].unit}
	return _contract_record(doc)


def _snapshot(doc):
	value = doc.terms_snapshot
	if not value:
		return {}
	return value if isinstance(value, dict) else frappe.parse_json(value)
