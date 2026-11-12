# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Inspection Report (CON-05; SRS v2.0 §3.1, §4.1; docs/CONSTRUCTION-CONTROLS_v0.2.md).

- Records a site inspection: date, inspector, checklist results, photos, defects, next action.
- The checklist, overall result, defects and next action must agree (services/construction.py).
- Photos are private files. The stage, if given, must be one of the job's stages.
- Approval (submit) is by the Sidra Inspector (SRS v1.6 §2: the Engineer / Inspector approves
  inspection reports). A submitted report does not change the job or certify a stage.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from sidra_realestate.services.construction import inspection_problems
from sidra_realestate.services.construction_jobs import (
	check_job_access,
	lock_job,
	refuse_closed,
	set_job_fields,
)


class SidraInspectionReport(Document):
	def validate(self):
		check_job_access(self, "read")
		set_job_fields(self)
		if getdate(self.inspection_date) > getdate(today()):
			frappe.throw(_("The inspection date cannot be in the future"))
		if self.next_action_due and getdate(self.next_action_due) < getdate(self.inspection_date):
			frappe.throw(_("The next action cannot be due before the inspection date"))
		if self.stage:
			stages = frappe.get_all(
				"Sidra Project Stage",
				filters={"parent": self.job, "parenttype": "Sidra Construction Job"},
				pluck="stage_name",
			)
			if self.stage not in stages:
				frappe.throw(_("Job {0} has no stage {1}").format(self.job, self.stage))
		problems = inspection_problems(self.result, self.checklist, self.defects_found, self.next_action)
		if problems:
			frappe.throw("<br>".join(problems), title=_("Inspection report is not consistent"))
		self.check_photos_private()

	def check_photos_private(self):
		for row in self.photos:
			if not row.photo:
				continue
			private = frappe.get_all("File", filters={"file_url": row.photo}, pluck="is_private")
			if not private or not all(private):
				frappe.throw(_("Photo row {0}: upload the photo as a private file").format(row.idx))

	def before_submit(self):
		refuse_closed(lock_job(self.job), _("an inspection report"))
		if not self.checklist:
			frappe.throw(_("Record at least one checklist result"))
