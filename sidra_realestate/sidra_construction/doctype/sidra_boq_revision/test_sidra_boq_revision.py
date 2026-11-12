# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""BOQ revisions (CON-02 revisions; docs/CONSTRUCTION-CONTROLS_v0.1.md §2)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import (
	OUTSIDER,
	PROJECT_MANAGER,
	as_user,
	ensure_base_records,
	make_job,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Construction Job", "Customer", "Company", "User", "UOM"]

BOQ = [
	{"cost_code": "01", "description": "Excavation", "qty": 12.5, "rate": 8},
	{"cost_code": "02", "description": "Concrete", "qty": 3, "rate": 145},
]


class TestSidraBOQRevision(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def revision(self, job, **values):
		return frappe.get_doc(
			{
				"doctype": "Sidra BOQ Revision",
				"job": job.name,
				"reason": "Client asked for a deeper footing",
				**values,
			}
		).insert(ignore_permissions=True)

	def approve(self, job, change_rate=150):
		rev = self.revision(job)
		rev.boq[1].rate = change_rate
		rev.save(ignore_permissions=True)
		rev.submit()
		return rev

	def test_draft_starts_from_job_boq(self):
		job = make_job(boq=BOQ)
		rev = self.revision(job)
		self.assertEqual(
			[(r.description, r.qty, r.rate) for r in rev.boq], [("Excavation", 12.5, 8), ("Concrete", 3, 145)]
		)
		self.assertEqual(rev.boq_total, 535)
		self.assertIsNone(rev.base_revision)
		self.assertEqual((rev.company, rev.customer), (job.company, job.customer))

	def test_approval_updates_job_and_numbers_revisions(self):
		job = make_job(boq=BOQ)
		rev = self.approve(job)
		self.assertEqual(
			(rev.revision_no, rev.previous_total, rev.boq_total, rev.difference), (1, 535, 550, 15)
		)
		self.assertEqual(rev.approved_by, "Administrator")
		job.reload()
		self.assertEqual((job.boq_revision, job.boq_revision_no, job.boq_total), (rev.name, 1, 550))
		self.assertEqual(job.boq[1].rate, 150)
		second = self.approve(job, change_rate=160)
		self.assertEqual((second.revision_no, second.base_revision), (2, rev.name))
		self.assertEqual(frappe.db.get_value("Sidra Construction Job", job.name, "boq_total"), 580)

	def test_job_boq_locked_after_approval(self):
		job = make_job(boq=BOQ)
		self.approve(job)
		job.reload()
		job.boq[0].qty = 20
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.append("boq", {"description": "Extra", "qty": 1, "rate": 1})
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.engineer = PROJECT_MANAGER  # other fields stay editable
		job.save(ignore_permissions=True)

	def test_revision_link_cannot_be_forged(self):
		job = make_job(boq=BOQ)
		rev = self.approve(job)
		job.reload()
		job.boq_revision = None
		job.boq_revision_no = 0
		job.save(ignore_permissions=True)
		self.assertEqual((job.boq_revision, job.boq_revision_no), (rev.name, 1))
		fresh = make_job(boq=BOQ, boq_revision=rev.name, boq_revision_no=4)
		self.assertEqual((fresh.boq_revision, fresh.boq_revision_no), (None, 0))

	def test_stale_draft_refused(self):
		job = make_job(boq=BOQ)
		stale = self.revision(job)
		stale.boq[0].rate = 9
		stale.save(ignore_permissions=True)
		self.approve(job)
		with self.assertRaises(frappe.ValidationError):
			stale.submit()

	def test_no_change_refused(self):
		job = make_job(boq=BOQ)
		with self.assertRaises(frappe.ValidationError):
			self.revision(job).submit()

	def test_needs_reason_and_lines(self):
		job = make_job(boq=BOQ)
		with self.assertRaises(frappe.ValidationError):
			self.revision(job, reason=" ")
		with self.assertRaises(frappe.ValidationError):
			self.revision(make_job())  # no BOQ to start from
		with self.assertRaises(frappe.ValidationError):
			self.revision(job, boq=[{"description": "Credit", "qty": -1, "rate": 5}])

	def test_cancel_refused(self):
		rev = self.approve(make_job(boq=BOQ))
		with self.assertRaises(frappe.ValidationError):
			rev.cancel()

	def test_closed_job_refused(self):
		job = make_job(boq=BOQ, status="Closed")
		rev = self.revision(job)
		rev.boq[0].rate = 9
		rev.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			rev.submit()

	def test_outsider_cannot_create(self):
		job = make_job(boq=BOQ)
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Sidra BOQ Revision", "job": job.name, "reason": "x"}).insert()

	def test_project_manager_approves(self):
		job = make_job(boq=BOQ)
		with as_user(PROJECT_MANAGER):
			rev = frappe.get_doc(
				{"doctype": "Sidra BOQ Revision", "job": job.name, "reason": "Rate update"}
			).insert()
			rev.boq[0].rate = 10
			rev.save()
			rev.submit()
		self.assertEqual(rev.approved_by, PROJECT_MANAGER)
