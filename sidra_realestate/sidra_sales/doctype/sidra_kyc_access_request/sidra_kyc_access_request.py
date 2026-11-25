# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra KYC Access Request: the General Manager's approval for one buyer's identity record (G32).

- A Sidra Sales Manager or the General Manager asks for one staff member to see one buyer's
  identity record (Sidra Customer KYC), with a reason.
- Only the General Manager approves, refuses or revokes, and sets the last day of access
  (30 days by default). Approval shares that one record with that one person, read only: they can
  view it and download its identity documents (G32 counts download and export as the same
  approval). They cannot edit or re-share it.
- Access ends when the General Manager revokes it or, automatically, after its last day
  (`expire_access`, daily). The share is removed; the request stays as the record.
- Any other share of a KYC record is still refused (identity_access.py).
"""

import frappe
import frappe.share
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime, today

KYC = "Sidra Customer KYC"
REQUEST = "Sidra KYC Access Request"
REQUESTERS = ("Sidra Sales Manager", "Sidra General Manager")
GM = "Sidra General Manager"
DEFAULT_DAYS = 30
OPEN = ("Pending", "Approved")
DECISION_FIELDS = ("status", "valid_until", "decided_by", "decided_on", "decision_note", "ended_on")
REQUEST_FIELDS = ("requested_by", "requested_on")


class SidraKYCAccessRequest(Document):
	def validate(self):
		before = None if self.is_new() else self.get_doc_before_save()
		if self.is_new():
			self.check_requester()
			self.status = "Pending"
			self.requested_by = frappe.session.user
			self.requested_on = now_datetime()
			for field in DECISION_FIELDS[1:]:
				self.set(field, None)
		elif not self.flags.deciding:
			for field in DECISION_FIELDS + REQUEST_FIELDS:
				self.set(field, before.get(field) if before else self.get(field))
			if before and before.status != "Pending" and self.reason != before.reason:
				frappe.throw(_("The reason can no longer change after the General Manager's decision"))
		if self.is_new() or self.flags.approving:
			self.check_user()

	def check_requester(self):
		if frappe.session.user == "Administrator":
			return
		if not set(REQUESTERS) & set(frappe.get_roles()):
			frappe.throw(
				_("Only a Sales Manager or the General Manager can ask for identity access"),
				frappe.PermissionError,
			)

	def check_user(self):
		if not frappe.db.exists("User", {"name": self.user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("Choose an enabled staff user"))
		open_request = frappe.db.get_value(
			REQUEST,
			{"kyc": self.kyc, "user": self.user, "status": ["in", OPEN], "name": ["!=", self.name]},
		)
		if open_request:
			frappe.throw(
				_("{0} already has an open request for this buyer: {1}").format(self.user, open_request)
			)
		if self.is_new() and role_can_read(self.kyc, self.user):
			frappe.throw(_("{0} can already read this buyer's identity record").format(self.user))


def role_can_read(kyc, user):
	"""Whether `user` reads the record through their roles, leaving out any share."""
	share = frappe.db.get_value("DocShare", {"share_doctype": KYC, "share_name": kyc, "user": user})
	if share:
		return False
	return bool(frappe.has_permission(KYC, "read", doc=kyc, user=user))


def decide(name):
	frappe.only_for(GM)
	if not frappe.db.get_value(REQUEST, name, "name", for_update=True):
		frappe.throw(_("Unknown request {0}").format(name), frappe.DoesNotExistError)
	doc = frappe.get_doc(REQUEST, name)
	doc.check_permission("write")
	doc.flags.deciding = True
	return doc


def record(doc, status, note=None, **values):
	doc.update(
		{
			"status": status,
			"decided_by": frappe.session.user,
			"decided_on": now_datetime(),
			"decision_note": note or doc.decision_note,
			**values,
		}
	)
	doc.save()


@frappe.whitelist(methods=["POST"])
def approve(name: str, valid_until: str | None = None, note: str | None = None):
	doc = decide(name)
	if doc.status != "Pending":
		frappe.throw(_("Request {0} is {1}, not Pending").format(name, doc.status))
	until = getdate(valid_until) if valid_until else getdate(add_days(today(), DEFAULT_DAYS))
	if until < getdate(today()):
		frappe.throw(_("The last day of access cannot be in the past"))
	if role_can_read(doc.kyc, doc.user):
		frappe.throw(_("{0} can already read this buyer's identity record").format(doc.user))
	doc.flags.approving = True
	record(doc, "Approved", note, valid_until=until)
	frappe.share.add_docshare(
		KYC,
		doc.kyc,
		user=doc.user,
		read=1,
		write=0,
		share=0,
		flags={"ignore_share_permission": True, "sidra_kyc_access_request": doc.name},
		notify=0,
	)
	frappe.get_doc(KYC, doc.kyc).add_comment(
		"Info",
		_("Identity access for {0} approved by {1} until {2} ({3})").format(
			doc.user, doc.decided_by, until, doc.name
		),
	)
	return {"status": doc.status, "valid_until": str(until)}


@frappe.whitelist(methods=["POST"])
def refuse(name: str, note: str | None = None):
	doc = decide(name)
	if doc.status != "Pending":
		frappe.throw(_("Request {0} is {1}, not Pending").format(name, doc.status))
	if not (note or "").strip():
		frappe.throw(_("Give a reason for refusing"))
	record(doc, "Refused", note)
	return {"status": doc.status}


@frappe.whitelist(methods=["POST"])
def revoke(name: str, note: str | None = None):
	doc = decide(name)
	if doc.status != "Approved":
		frappe.throw(_("Only approved access can be revoked; request {0} is {1}").format(name, doc.status))
	end_access(doc, "Revoked", note)
	return {"status": doc.status}


def end_access(doc, status, note=None):
	share = frappe.db.get_value("DocShare", {"share_doctype": KYC, "share_name": doc.kyc, "user": doc.user})
	if share:
		frappe.delete_doc("DocShare", share, ignore_permissions=True, flags={"ignore_share_permission": True})
	if status == "Expired":
		doc.update({"status": status, "ended_on": now_datetime()})
		doc.save(ignore_permissions=True)
	else:
		record(doc, status, note, ended_on=now_datetime())
	frappe.get_doc(KYC, doc.kyc).add_comment(
		"Info", _("Identity access for {0} ended: {1} ({2})").format(doc.user, status, doc.name)
	)


def expire_access():
	"""Daily: end every approved access whose last day has passed."""
	for name in frappe.get_all(
		REQUEST, filters={"status": "Approved", "valid_until": ["<", today()]}, pluck="name"
	):
		doc = frappe.get_doc(REQUEST, name)
		doc.flags.deciding = True
		end_access(doc, "Expired")


def approved_request(name, kyc, user):
	"""The approved, current request `name` for exactly this record and person, else None."""
	request = frappe.db.get_value(REQUEST, name, ["kyc", "user", "status", "valid_until"], as_dict=True)
	if not request or request.status != "Approved" or (request.kyc, request.user) != (kyc, user):
		return None
	if not request.valid_until or getdate(request.valid_until) < getdate(today()):
		return None
	return request
