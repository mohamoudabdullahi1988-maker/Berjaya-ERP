"""ERPNext Projects and Tasks for the pilot's construction jobs (G37) on the disposable CI site.

Run by `test_demo_datasets.TestDemo6Projects`, after the pilot dataset is loaded.
"""

from unittest.mock import patch

import frappe

from sidra_realestate.finance_demo import COMPANY, FLAGS
from sidra_realestate.pilot_demo import MANIFEST as PILOT_MANIFEST
from sidra_realestate.pilot_demo import _read_manifest
from sidra_realestate.pilot_projects import create_pilot_projects
from sidra_realestate.tests.helpers import as_user


class PilotProjectsChecks:
	def test_pilot_jobs_get_projects_once_and_post_nothing(self):
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 0 for flag in FLAGS}):
			with self.assertRaisesRegex(frappe.ValidationError, "staging-only flags"):
				create_pilot_projects()
		with patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}), as_user("sidra.manager@example.com"):
			with self.assertRaises(frappe.PermissionError):
				create_pilot_projects()

		gl_before = frappe.db.count("GL Entry")
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			jobs = _read_manifest(PILOT_MANIFEST, None)["jobs"]["jobs"]
			data = create_pilot_projects()
			self.assertTrue(data["created"])
			self.assertTrue(data["projects"])
			self.assertEqual(set(data["projects"]) | set(data["skipped"]), set(jobs))
			for job, project in data["projects"].items():
				self.assertEqual(frappe.db.get_value("Sidra Construction Job", job, "project"), project)
				self.assertEqual(
					frappe.db.get_value("Project", project, ["company", "sidra_construction_job"]),
					(COMPANY, job),
				)
				stages = frappe.db.count("Sidra Project Stage", {"parent": job})
				self.assertEqual(frappe.db.count("Task", {"project": project}), stages)
			self.assertEqual(
				data["tasks"], frappe.db.count("Task", {"project": ["in", list(data["projects"].values())]})
			)

			again = create_pilot_projects()
			self.assertFalse(again["created"])
			self.assertEqual(
				frappe.db.count("Project", {"sidra_construction_job": ["in", jobs]}), len(data["projects"])
			)
		self.assertEqual(frappe.db.count("GL Entry"), gl_before)
