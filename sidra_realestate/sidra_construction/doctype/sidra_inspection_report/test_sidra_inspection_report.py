# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Site inspection reports (CON-05; docs/CONSTRUCTION-CONTROLS_v0.2.md §4)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.tests.helpers import (
	INSPECTOR,
	OUTSIDER,
	PROJECT_MANAGER,
	as_user,
	ensure_base_records,
	make_job,
	site_photo,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Construction Job", "Customer", "Company", "User", "UOM"]


class TestSidraInspectionReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def report(self, job=None, user=INSPECTOR, **values):
		job = job or make_job(status="In Progress")
		with as_user(user):
			return frappe.get_doc(
				{
					"doctype": "Sidra Inspection Report",
					"job": job.name,
					"inspector": INSPECTOR,
					"inspection_date": today(),
					"result": "Pass",
					"checklist": [
						{"item": "Rebar spacing", "result": "Pass"},
						{"item": "Formwork", "result": "Not Applicable"},
					],
					**values,
				}
			).insert()

	def test_inspector_records_and_approves(self):
		job = make_job(status="In Progress")
		doc = self.report(job, stage="Foundation", photos=[{"photo": site_photo(), "caption": "Footing"}])
		self.assertEqual((doc.company, doc.customer), (job.company, job.customer))
		with as_user(INSPECTOR):
			doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_failed_checks_need_defects_and_next_action(self):
		failed = [{"item": "Concrete cover", "result": "Fail", "remarks": "15 mm on slab edge"}]
		with self.assertRaises(frappe.ValidationError):
			self.report(checklist=failed)  # result Pass with a failed check
		with self.assertRaises(frappe.ValidationError):
			self.report(checklist=failed, result="Fail")  # no defects or next action
		with self.assertRaises(frappe.ValidationError):
			self.report(
				checklist=[{"item": "Cover", "result": "Fail"}],
				result="Fail",
				defects_found="x",
				next_action="y",
			)
		doc = self.report(
			checklist=failed,
			result="Fail",
			defects_found="Low cover on the slab edge",
			next_action="Break out and re-pour the edge",
			next_action_due=add_days(today(), 7),
		)
		self.assertEqual(doc.result, "Fail")

	def test_dates_checked(self):
		with self.assertRaises(frappe.ValidationError):
			self.report(inspection_date=add_days(today(), 1))
		with self.assertRaises(frappe.ValidationError):
			self.report(
				result="Pass with defects",
				defects_found="Cracks",
				next_action="Monitor",
				inspection_date=add_days(today(), -3),
				next_action_due=add_days(today(), -4),
			)

	def test_stage_must_be_on_job(self):
		with self.assertRaises(frappe.ValidationError):
			self.report(stage="Swimming pool")

	def test_photos_must_be_private(self):
		with self.assertRaises(frappe.ValidationError):
			self.report(photos=[{"photo": site_photo(is_private=0)}])

	def test_project_manager_drafts_but_cannot_approve(self):
		doc = self.report(user=PROJECT_MANAGER)
		with as_user(PROJECT_MANAGER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Sidra Inspection Report", doc.name).submit()

	def test_outsider_cannot_create(self):
		with self.assertRaises(frappe.PermissionError):
			self.report(user=OUTSIDER)

	def test_cancelled_job_refused(self):
		job = make_job(status="In Progress")
		doc = self.report(job)
		frappe.db.set_value("Sidra Construction Job", job.name, "status", "Cancelled")
		with as_user(INSPECTOR), self.assertRaises(frappe.ValidationError):
			doc.submit()
