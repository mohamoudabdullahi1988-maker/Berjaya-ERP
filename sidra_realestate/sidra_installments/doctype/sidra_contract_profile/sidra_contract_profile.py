# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Contract profile (INS-18; SRS v1.6 §5.5; SRS v2.0 §3.3).

P0 stores every setting but applies only the payment plan. Contracts copy the profile
into a frozen snapshot when they are first saved (INS-20).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

HOLD_ROLE = "Sidra General Manager"

# Settings copied into a contract's terms snapshot.
TERM_FIELDS = (
	"profile_name",
	"legal_hold",
	"installments",
	"due_day",
	"grace_months",
	"down_payment_type",
	"down_payment_value",
	"markup_rate",
	"early_payment",
	"penalty_type",
	"penalty_per_day",
	"penalty_monthly_cap",
	"penalty_fixed_amount",
	"notice_days",
	"penalty_destination",
	"default_trigger_missed",
	"refund_retention_type",
	"refund_retention_value",
	"title_deadline_days",
	"title_deadline_note",
	"title_penalty_type",
	"title_penalty_amount",
	"title_refund_after_days",
	"title_refund_compensation_pct",
)


class SidraContractProfile(Document):
	def validate(self):
		self.check_range("installments", 1, 60)
		self.check_range("due_day", 1, 28)
		self.check_range("grace_months", 0, 12)
		self.check_range("notice_days", 0, 60)
		self.check_not_negative(
			"down_payment_value",
			"markup_rate",
			"penalty_per_day",
			"penalty_monthly_cap",
			"penalty_fixed_amount",
			"default_trigger_missed",
			"refund_retention_value",
			"title_deadline_days",
			"title_penalty_amount",
			"title_refund_after_days",
			"title_refund_compensation_pct",
		)
		if self.down_payment_type in ("Fixed", "Percent") and not self.down_payment_value:
			frappe.throw(_("Enter the down payment amount or percentage"))
		if self.down_payment_type == "Percent" and self.down_payment_value > 100:
			frappe.throw(_("A down payment percentage cannot exceed 100"))
		if not self.legal_hold and not self.title_deadline_days:
			frappe.throw(_("Set the title deadline, or put the profile on legal hold"))
		if self.is_default and not self.active:
			frappe.throw(_("The default profile must be active"))
		self.penalty_destination = "Pending Policy Sign-off"
		self.validate_legal_hold_change()

	def check_range(self, field, low, high):
		value = cint(self.get(field))
		if not low <= value <= high:
			frappe.throw(_("{0} must be from {1} to {2}").format(self.meta.get_label(field), low, high))

	def check_not_negative(self, *fields):
		for field in fields:
			if (self.get(field) or 0) < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)))

	def validate_legal_hold_change(self):
		before = self.get_doc_before_save()
		if before and before.legal_hold and not self.legal_hold and HOLD_ROLE not in frappe.get_roles():
			frappe.throw(_("Only the General Manager can lift a legal hold"), frappe.PermissionError)

	def on_update(self):
		if self.is_default:
			for other in frappe.get_all(
				"Sidra Contract Profile", filters={"is_default": 1, "name": ("!=", self.name)}, pluck="name"
			):
				frappe.db.set_value("Sidra Contract Profile", other, "is_default", 0)

	def on_trash(self):
		if frappe.db.exists("Sidra Sale Contract", {"contract_profile": self.name}):
			frappe.throw(_("Profile {0} is used by contracts; retire it instead").format(self.name))

	def terms(self) -> dict:
		"""The settings a contract freezes when it is first saved."""
		return {field: self.get(field) for field in TERM_FIELDS}
