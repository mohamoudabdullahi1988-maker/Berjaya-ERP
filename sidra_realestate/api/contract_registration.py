# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Register an External contract from the Berjaya interface (implementation plan Phase 4).

Three whitelisted methods. Every rule stays in the Sidra Sale Contract controller; this module
only decides which fields the interface may set and adds the checks a second screen needs:

- `save_registration_draft` creates or updates a draft registered (External) installment
  contract. Only the fields in `HEADER_FIELDS`, `UNIT_FIELDS` and `SCHEDULE_FIELDS` can be
  set from here (rules audit R7: a field hidden on a screen must not be writable through it).
  Penalty, default, title and party terms are edited in Desk for now.
- `attach_registration_copy` puts an uploaded File on the draft's Signed Copy field, after
  checking it is this contract's own private file.
- `confirm_registration` submits the draft. Only a user with submit permission (the Sidra
  Sales Manager, decision D7) can. The controller's confirmation gate runs unchanged.

Safeguards for a second interface:
- **Stale edits are refused.** Each change carries the `modified` value the user loaded; if the
  saved record has changed since, nothing is written and the reason names who changed it.
- **The row is locked** (`SELECT ... FOR UPDATE`) before it is checked and written, so two
  confirmations of one draft cannot both run.
- **Retries are safe.** A create carries a `request_key`: a retry with the same key returns the
  draft the first call made. A confirmation repeated by the same user after it succeeded returns
  the same result and changes nothing. Nothing in this module posts a voucher, payment or ledger
  entry (`CLAUDE.md` rule 3); confirmation marks the units Under Contract, as in Desk.
- **A schedule difference must be acknowledged** (rules audit R1). A difference within the
  tolerance can be confirmed only with `acknowledge_difference=1`, and the acknowledgement is
  recorded on the contract as a comment naming the user and the amount. Above the tolerance the
  controller refuses as before. Desk keeps its own confirmation dialog.
"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, fmt_money, get_fullname

from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	schedule_tolerance,
)
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import EXTERNAL

DOCTYPE = "Sidra Sale Contract"

# What the registration screen may set. Anything else in the payload is refused.
HEADER_FIELDS = (
	"customer",
	"company",
	"signed_on",
	"external_reference",
	"agreed_price",
	"contract_profile",
	"down_payment_mode",
	"down_payment",
	"installments",
	"due_day",
	"grace_months",
	"terms_summary",
)
UNIT_FIELDS = ("unit", "allocated_price")
SCHEDULE_FIELDS = ("row_type", "due_date", "amount")
TABLES = {"units": UNIT_FIELDS, "schedule": SCHEDULE_FIELDS}

REQUEST_KEY_TTL = 24 * 60 * 60  # seconds a create's request key is remembered


class StaleRecord(frappe.ValidationError):
	"""The record changed after the user loaded it."""


# ---------------------------------------------------------------------- methods
@frappe.whitelist(methods=["POST"])
def save_registration_draft(
	data: dict | str,
	contract: str | None = None,
	expected_modified: str | None = None,
	request_key: str | None = None,
) -> dict:
	"""Create (no `contract`) or update a draft registered contract. Returns its name and `modified`."""
	values = clean_payload(frappe.parse_json(data) if isinstance(data, str) else data)

	if not contract:
		earlier = _remembered(request_key)
		if earlier and frappe.db.exists(DOCTYPE, earlier):
			return _result(frappe.get_doc(DOCTYPE, earlier), repeated=True)
		frappe.has_permission(DOCTYPE, "create", throw=True)
		doc = frappe.new_doc(DOCTYPE)
		doc.contract_type = "Installment"
		doc.source = EXTERNAL
		apply_values(doc, values)
		doc.insert()
		_remember(request_key, doc.name)
		return _result(doc)

	doc = _locked(contract)
	doc.check_permission("write")
	_check_registration_draft(doc)
	check_not_stale(doc, expected_modified)
	apply_values(doc, values)
	doc.save()
	return _result(doc)


@frappe.whitelist(methods=["POST"])
def attach_registration_copy(contract: str, file_url: str, expected_modified: str | None = None) -> dict:
	"""Set an uploaded File as the draft's original signed contract.

	The file must already be attached to this contract's Signed Copy field and be private; the
	controller checks the rest (on disk, readable, not shared) again at confirmation."""
	doc = _locked(contract)
	doc.check_permission("write")
	_check_registration_draft(doc)
	check_not_stale(doc, expected_modified)
	files = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=["name", "is_private", "attached_to_doctype", "attached_to_name", "attached_to_field"],
	)
	own = [
		row
		for row in files
		if (row.attached_to_doctype, row.attached_to_name, row.attached_to_field)
		== (DOCTYPE, doc.name, "signed_copy")
	]
	if not own:
		frappe.throw(_("Upload the file to this contract's Signed Copy field first"))
	if len(own) != len(files):
		frappe.throw(_("This file is also used by another record; upload this contract's own scan"))
	if not own[0].is_private:
		frappe.throw(_("The signed copy must be a private file"))
	doc.signed_copy = file_url
	doc.save()
	return _result(doc)


@frappe.whitelist(methods=["POST"])
def confirm_registration(
	contract: str, expected_modified: str | None = None, acknowledge_difference: int = 0
) -> dict:
	"""Confirm (submit) a draft registered contract: decision D7, the Sales Manager's approval."""
	doc = _locked(contract)
	doc.check_permission("read")
	if doc.docstatus == 1:
		# A repeat of a confirmation that already succeeded changes nothing.
		if doc.terms_approved_by == frappe.session.user:
			return _result(doc, repeated=True)
		frappe.throw(
			_("{0} was already confirmed by {1}").format(doc.name, get_fullname(doc.terms_approved_by))
		)
	_check_registration_draft(doc)
	doc.check_permission("submit")
	check_not_stale(doc, expected_modified)

	difference = flt(doc.schedule_difference, 2)
	if difference and abs(difference) <= schedule_tolerance() and not cint(acknowledge_difference):
		frappe.throw(
			_(
				"The schedule differs from the amount due by {0}. Acknowledge the difference to confirm."
			).format(_money(doc, difference)),
			title=_("Acknowledge the difference"),
		)

	doc.submit()
	if difference:
		doc.add_comment(
			"Info",
			_("Schedule difference of {0} acknowledged by {1} at confirmation.").format(
				_money(doc, difference), get_fullname(frappe.session.user)
			),
		)
	return _result(doc)


# ---------------------------------------------------------------------- helpers
def clean_payload(values) -> dict:
	"""Keep only the fields the screen may set; refuse anything else instead of ignoring it."""
	if not isinstance(values, dict):
		frappe.throw(_("Send the contract's values as an object"))
	allowed = set(HEADER_FIELDS) | set(TABLES)
	unknown = sorted(set(values) - allowed)
	if unknown:
		frappe.throw(_("These fields cannot be set from this screen: {0}").format(", ".join(unknown)))
	cleaned = {field: values[field] for field in HEADER_FIELDS if field in values}
	for table, fields in TABLES.items():
		if table not in values:
			continue
		rows = values[table]
		if not isinstance(rows, list):
			frappe.throw(_("{0} must be a list of rows").format(table))
		cleaned[table] = []
		for number, row in enumerate(rows, start=1):
			if not isinstance(row, dict):
				frappe.throw(_("{0} row {1} must be an object").format(table, number))
			extra = sorted(set(row) - set(fields))
			if extra:
				frappe.throw(
					_("{0} row {1}: these fields cannot be set here: {2}").format(
						table, number, ", ".join(extra)
					)
				)
			cleaned[table].append({field: row.get(field) for field in fields})
	return cleaned


def apply_values(doc, values):
	"""Header fields are set as given; a table sent is replaced whole, in the order sent."""
	for field in HEADER_FIELDS:
		if field in values:
			doc.set(field, values[field])
	for table in TABLES:
		if table in values:
			doc.set(table, [])
			for row in values[table]:
				doc.append(table, row)


def check_not_stale(doc, expected_modified):
	"""Refuse to write over a change the user has not seen."""
	if not expected_modified:
		frappe.throw(_("Reload the contract before changing it"), StaleRecord)
	if cstr(doc.modified) != cstr(expected_modified):
		frappe.throw(
			_("{0} was changed by {1} after you opened it. Reload it and make your change again.").format(
				doc.name, get_fullname(doc.modified_by)
			),
			StaleRecord,
		)


def _check_registration_draft(doc):
	if doc.docstatus != 0:
		frappe.throw(_("{0} is not a draft and cannot be changed here").format(doc.name))
	if not doc.is_external():
		frappe.throw(_("Only a registered (External) installment contract can be edited on this screen"))


def _locked(contract):
	"""Lock the contract's row for this transaction, then load it."""
	if not frappe.db.get_value(DOCTYPE, contract, "name", for_update=True):
		frappe.throw(_("{0} {1} not found").format(_(DOCTYPE), contract), frappe.DoesNotExistError)
	return frappe.get_doc(DOCTYPE, contract)


def _result(doc, repeated=False):
	return {
		"name": doc.name,
		"modified": cstr(doc.modified),
		"docstatus": doc.docstatus,
		"repeated": repeated,
	}


def _money(doc, value):
	return fmt_money(flt(value, 2), precision=2, currency=doc.currency)


def _request_cache_key(request_key):
	return f"berjaya:registration:create:{frappe.session.user}:{request_key}"


def _remembered(request_key):
	if not request_key:
		return None
	return frappe.cache.get_value(_request_cache_key(request_key))


def _remember(request_key, name):
	if request_key:
		frappe.cache.set_value(_request_cache_key(request_key), name, expires_in_sec=REQUEST_KEY_TTL)
