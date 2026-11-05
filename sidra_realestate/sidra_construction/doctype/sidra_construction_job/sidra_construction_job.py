# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Construction Job (CON-01, CON-02, CON-04 partial; SRS v2.0 §3.1, §6).

Planning only: stages and BOQ entry. No billing, costing or certification in P0.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

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
		self.validate_project()
		self.validate_stages()
		self.set_boq_amounts()

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
