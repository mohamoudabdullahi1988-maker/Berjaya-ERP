# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G37: a construction job is planned as an ERPNext Project with one Task per stage."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.services.construction_projects import create_project
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	INSPECTOR,
	OUTSIDER,
	PROJECT_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	ensure_user,
	make_job,
)

JOB = "Sidra Construction Job"
FINANCE = "sidra.finance@example.com"


def tasks(job):
	return {
		t.sidra_job_stage: t
		for t in frappe.get_all(
			"Task",
			filters={"sidra_construction_job": job},
			fields=[
				"name",
				"subject",
				"project",
				"status",
				"progress",
				"exp_start_date",
				"exp_end_date",
				"completed_on",
				"sidra_job_stage",
				"sidra_billing_pct",
				"sidra_certified",
			],
		)
	}


class TestConstructionProjects(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_user(FINANCE, ["Sidra Finance Reviewer"])

	def job(self, **values):
		start = add_days(today(), -30)
		job = make_job(plot_number="_Test plot 7", **values)
		for i, row in enumerate(job.stages):
			row.planned_start = add_days(start, i * 10)
			row.planned_end = add_days(start, i * 10 + 9)
		job.save(ignore_permissions=True)
		return job

	def test_project_and_one_task_per_stage(self):
		job = self.job()
		with as_user(PROJECT_MANAGER):
			project = create_project(job.name)["project"]
		job.reload()
		self.assertEqual(job.project, project)
		values = frappe.db.get_value(
			"Project",
			project,
			["company", "customer", "sidra_construction_job", "expected_start_date", "expected_end_date"],
			as_dict=True,
		)
		self.assertEqual((values.company, values.customer), (COMPANY, BUYER))
		self.assertEqual(values.sidra_construction_job, job.name)
		self.assertEqual(getdate(values.expected_start_date), getdate(job.stages[0].planned_start))
		self.assertEqual(getdate(values.expected_end_date), getdate(job.stages[-1].planned_end))

		mirrored = tasks(job.name)
		self.assertEqual(set(mirrored), {row.name for row in job.stages})
		for row in job.stages:
			task = mirrored[row.name]
			self.assertEqual(task.project, project)
			self.assertEqual(task.subject, f"{row.idx}. {row.stage_name}")
			self.assertEqual(task.status, "Open")
			self.assertEqual(getdate(task.exp_start_date), getdate(row.planned_start))

	def test_tasks_follow_the_stages(self):
		job = self.job()
		with as_user(PROJECT_MANAGER):
			create_project(job.name)
		job.reload()
		first, second = job.stages[0], job.stages[1]
		first.update(
			{
				"status": "Completed",
				"completion_pct": 100,
				"actual_start": add_days(today(), -5),
				"actual_end": today(),
			}
		)
		second.update({"status": "In Progress", "completion_pct": 40})
		job.append("stages", {"stage_name": "_Test extra stage"})
		job.save(ignore_permissions=True)

		mirrored = tasks(job.name)
		self.assertEqual(mirrored[first.name].status, "Completed")
		self.assertEqual(getdate(mirrored[first.name].completed_on), getdate(today()))
		self.assertEqual(mirrored[second.name].status, "Working")
		self.assertEqual(mirrored[second.name].progress, 40)
		self.assertIn(job.stages[-1].name, mirrored)

		removed = job.stages[-1].name
		job.stages = job.stages[:-1]
		job.save(ignore_permissions=True)
		self.assertEqual(tasks(job.name)[removed].status, "Cancelled")

	def test_certification_reaches_the_task(self):
		from sidra_realestate.sidra_construction.doctype.sidra_construction_job.sidra_construction_job import (
			certify_stage,
		)

		job = self.job()
		with as_user(PROJECT_MANAGER):
			create_project(job.name)
		job.reload()
		row = job.stages[0]
		row.update({"status": "Completed", "completion_pct": 100, "actual_end": today()})
		job.save(ignore_permissions=True)
		with as_user(PROJECT_MANAGER):
			certify_stage(job.name, row.name)
		self.assertEqual(tasks(job.name)[row.name].sidra_certified, 1)

	def test_who_may_create_a_project(self):
		job = self.job()
		for user in (SALES_USER, INSPECTOR, FINANCE, OUTSIDER):
			with self.subTest(user=user), as_user(user), self.assertRaises(frappe.PermissionError):
				create_project(job.name)
		self.assertFalse(frappe.db.get_value(JOB, job.name, "project"))

	def test_one_project_per_job_and_none_for_closed_jobs(self):
		job = self.job()
		with as_user(PROJECT_MANAGER):
			create_project(job.name)
			with self.assertRaises(frappe.ValidationError):
				create_project(job.name)
		closed = self.job()
		frappe.db.set_value(JOB, closed.name, "status", "Cancelled")
		with as_user(PROJECT_MANAGER), self.assertRaises(frappe.ValidationError):
			create_project(closed.name)

	def test_a_hand_linked_project_is_left_alone(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test hand-made project",
				"company": COMPANY,
				"customer": BUYER,
			}
		).insert(ignore_permissions=True)
		job = self.job(project=project.name)
		job.save(ignore_permissions=True)
		self.assertFalse(tasks(job.name))
