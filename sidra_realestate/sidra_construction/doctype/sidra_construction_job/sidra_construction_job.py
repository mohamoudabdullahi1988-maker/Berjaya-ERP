# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Construction Job (CON-01, CON-02, CON-03, CON-04, CON-06; SRS v2.0 §3.1, §6).

Stages, BOQ and contract. P1 controls (docs/CONSTRUCTION-CONTROLS_v0.2.md; decision G11):
- once a BOQ revision is approved, the BOQ changes only through a new Sidra BOQ Revision;
- the contract terms (value, dates, retention) are set only when the General Manager approves an
  accepted Sidra Construction Quotation (CON-03); stage Billing % are the payment milestones, must
  add up to 100 and cannot change after that;
- approved variations, the current contract value and each stage's milestone amount are
  recalculated from submitted variation orders on every save;
- a stage certified by the Project Manager (`certify_stage`) can no longer be changed or removed.
Certification is a record of completion, not an invoice or revenue (CON-07 waits for P2).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from sidra_realestate.services.construction import (
	CLOSED_STATUSES,
	billing_pct_problem,
	boq_key,
	milestone_amounts,
	money,
)
from sidra_realestate.services.construction_jobs import approved_variation_amounts, lock_job

STAGE_FIELDS = (
	"stage_name",
	"status",
	"planned_start",
	"planned_end",
	"actual_start",
	"actual_end",
	"completion_pct",
	"billing_pct",
	"engineer",
)
STAGE_DATES = ("planned_start", "planned_end", "actual_start", "actual_end")
CERTIFICATION_FIELDS = ("certified", "certified_by", "certified_on")
BOQ_FIELDS = ("cost_code", "description", "uom", "qty", "rate")
CONTRACT_FIELDS = (
	"contract_quotation",
	"contract_value",
	"contract_start_date",
	"contract_duration_days",
	"contract_end_date",
	"retention_pct",
	"retention_period_months",
	"contract_approved_by",
	"contract_approved_on",
)

# SRS v1.6 §3.1 stage templates; a job copies one when it is created without stages.
STAGE_TEMPLATES = {
	"Full Construction": [
		"Site survey",
		"Design",
		"Permit",
		"Foundation",
		"Structure",
		"Roofing",
		"Finishing",
		"Handover",
		"Defects period",
	],
	"Design Only": ["Brief", "Concept", "Detailed drawings", "BOQ", "Delivery"],
	"Inspection Only": ["Request", "Scheduled visit", "Report", "Delivery"],
}


class SidraConstructionJob(Document):
	def before_insert(self):
		if not self.stages:
			for stage in STAGE_TEMPLATES.get(self.service_type, []):
				self.append("stages", {"stage_name": stage})

	def validate(self):
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.validate_project()
		before = None
		if not self.is_new():
			# The stored job decides what is locked; never trust a missing copy as "nothing locked".
			before = self.get_doc_before_save() or frappe.get_doc(self.doctype, self.name)
		self.validate_stages()
		self.protect_certified_stages(before)
		self.set_boq_amounts()
		self.protect_boq(before)
		self.protect_contract(before)
		self.set_contract_values()

	def validate_project(self):
		if not self.project:
			return
		project = frappe.db.get_value("Project", self.project, ["company", "customer"], as_dict=True)
		if not project:
			frappe.throw(_("Unknown project {0}").format(self.project), frappe.DoesNotExistError)
		if project.company != self.company:
			frappe.throw(
				_("Project {0} belongs to {1}, not {2}").format(self.project, project.company, self.company)
			)
		if project.customer and project.customer != self.customer:
			frappe.throw(_("Project {0} is for customer {1}").format(self.project, project.customer))

	def validate_stages(self):
		total_billing = 0
		for row in self.stages:
			for field in ("completion_pct", "billing_pct"):
				if not 0 <= flt(row.get(field)) <= 100:
					frappe.throw(_("Stage {0}: percentages must be from 0 to 100").format(row.idx))
			total_billing += flt(row.billing_pct)
			for start, end in (("planned_start", "planned_end"), ("actual_start", "actual_end")):
				if row.get(start) and row.get(end) and getdate(row.get(end)) < getdate(row.get(start)):
					frappe.throw(_("Stage {0}: an end date is before its start date").format(row.idx))
		if flt(total_billing, 6) > 100:
			frappe.throw(_("Stage billing percentages add up to more than 100"))

	def set_boq_amounts(self):
		total = 0
		for row in self.boq:
			if flt(row.qty) < 0 or flt(row.rate) < 0:
				frappe.throw(_("BOQ row {0}: quantity and rate cannot be negative").format(row.idx))
			row.amount = flt(flt(row.qty) * flt(row.rate), 2)
			total += row.amount
		self.boq_total = flt(total, 2)

	def protect_certified_stages(self, before):
		"""Only `certify_stage` sets certification; a certified stage is frozen and stays on the job."""
		old = {row.name: row for row in before.stages} if before else {}
		for row in self.stages:
			prev = old.get(row.name)
			if self.flags.certifying_stage != row.name:
				for field in CERTIFICATION_FIELDS:
					row.set(field, prev.get(field) if prev else None)
				row.certified = row.certified or 0
			if prev and prev.certified and stage_values(row) != stage_values(prev):
				frappe.throw(
					_("Stage {0} ({1}) is certified and can no longer be changed").format(
						row.idx, prev.stage_name
					)
				)
		current = {row.name for row in self.stages}
		for name, prev in old.items():
			if prev.certified and name not in current:
				frappe.throw(_("Certified stage {0} cannot be removed").format(prev.stage_name))

	def protect_boq(self, before):
		if self.flags.boq_from_revision:
			return
		self.boq_revision = before.boq_revision if before else None
		self.boq_revision_no = before.boq_revision_no if before else 0
		if before and before.boq_revision and boq_key(boq_values(self)) != boq_key(boq_values(before)):
			frappe.throw(
				_(
					"This BOQ is controlled by approved revision {0}; change it through a new BOQ Revision"
				).format(before.boq_revision),
				title=_("BOQ is revision-controlled"),
			)

	def protect_contract(self, before):
		"""Contract terms come only from `approve_contract` on the accepted quotation (CON-03, G11)."""
		if not self.flags.contract_from_quotation:
			for field in CONTRACT_FIELDS:
				self.set(field, before.get(field) if before else None)
		if not self.contract_quotation:
			return
		problem = billing_pct_problem([row.billing_pct for row in self.stages])
		if problem:
			frappe.throw(_("The contract's payment milestones: {0}").format(_(problem)))
		if self.flags.contract_from_quotation or not before:
			return
		old = {row.name: flt(row.billing_pct, 6) for row in before.stages}
		new = {row.name: flt(row.billing_pct, 6) for row in self.stages}
		changed = [n for n, pct in old.items() if pct and new.get(n) != pct]
		added = [n for n, pct in new.items() if n not in old and pct]
		if changed or added:
			frappe.throw(
				_(
					"Stage Billing % are the contract's payment milestones and cannot change after the contract is approved"
				),
				title=_("Milestones locked"),
			)

	def set_contract_values(self):
		approved = sum(approved_variation_amounts(self.name), money(0)) if not self.is_new() else money(0)
		current = money(self.contract_value) + approved if self.contract_quotation else money(0)
		self.approved_variations = flt(approved, 2)
		self.current_contract_value = flt(current, 2)
		amounts = milestone_amounts(current, [row.billing_pct for row in self.stages])
		for row, amount in zip(self.stages, amounts, strict=True):
			row.billing_amount = flt(amount, 2)


def stage_values(row):
	values = []
	for field in STAGE_FIELDS:
		value = row.get(field)
		if field in STAGE_DATES:
			value = str(getdate(value)) if value else None
		elif field in ("completion_pct", "billing_pct"):
			value = flt(value, 6)
		else:
			value = value or None
		values.append(value)
	return tuple(values)


def boq_values(doc):
	return [{field: row.get(field) for field in BOQ_FIELDS} for row in doc.boq]


@frappe.whitelist()
def certify_stage(job: str, stage: str):
	"""CON-04 / CON-07 prerequisite: the Project Manager certifies a completed stage (SRS v1.6 §2).

	Records who and when. Creates no invoice and recognises no revenue.
	"""
	frappe.only_for("Sidra Project Manager")
	locked = lock_job(job)
	if locked.status in CLOSED_STATUSES:
		frappe.throw(_("Job {0} is {1}; stages cannot be certified").format(job, locked.status))
	doc = frappe.get_doc("Sidra Construction Job", job)
	doc.check_permission("write")
	row = next((r for r in doc.stages if r.name == stage), None)
	if not row:
		frappe.throw(_("Job {0} has no stage row {1}").format(job, stage), frappe.DoesNotExistError)
	if row.certified:
		frappe.throw(_("Stage {0} is already certified").format(row.stage_name))
	if row.status != "Completed" or flt(row.completion_pct, 6) != 100 or not row.actual_end:
		frappe.throw(
			_(
				"Stage {0} can be certified only when it is Completed, 100% complete and has an actual end date"
			).format(row.stage_name)
		)
	if getdate(row.actual_end) > getdate(today()):
		frappe.throw(_("Stage {0} ends in the future; it cannot be certified yet").format(row.stage_name))
	row.certified = 1
	row.certified_by = frappe.session.user
	row.certified_on = now_datetime()
	doc.flags.certifying_stage = row.name
	doc.save()
	doc.add_comment("Info", _("Stage {0} certified by {1}").format(row.stage_name, row.certified_by))
	return {"stage": row.name, "certified_by": row.certified_by, "certified_on": str(row.certified_on)}
