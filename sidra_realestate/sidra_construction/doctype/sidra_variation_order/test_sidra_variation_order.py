# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Variation orders (CON-06; decision G11; docs/CONSTRUCTION-CONTROLS_v0.2.md §4)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.tests.helpers import (
	GENERAL_MANAGER,
	INSPECTOR,
	OTHER_PROJECT_MANAGER,
	PROJECT_MANAGER,
	as_user,
	ensure_base_records,
	make_contracted_job,
	make_job,
	private_file,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Construction Job", "Customer", "Company", "User", "UOM"]

JOB = "Sidra Construction Job"
VO = "Sidra Variation Order"


class TestSidraVariationOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def raise_order(self, job, amount=800, attach=True, **values):
		"""Raised by the Project Manager with the client's approval recorded, as staff do."""
		with as_user(PROJECT_MANAGER):
			vo = frappe.get_doc(
				{
					"doctype": VO,
					"job": job.name,
					"amount": amount,
					"description": "Add a boundary wall on the east side",
					"client_approved_by": "_Test Buyer Amina",
					"client_approved_on": today(),
					**values,
				}
			).insert()
			if attach:
				vo.client_approval_document = private_file(
					name="client-approval.pdf", attached_to=vo, field="client_approval_document"
				)
				vo.save()
		return vo

	def approve(self, vo, user=OTHER_PROJECT_MANAGER):
		with as_user(user):
			doc = frappe.get_doc(VO, vo.name)
			doc.submit()
		return doc

	def totals(self, job):
		return tuple(frappe.db.get_value(JOB, job.name, ["approved_variations", "current_contract_value"]))

	def milestones(self, job):
		return [s.billing_amount for s in frappe.get_doc(JOB, job.name).stages]

	def test_additions_raise_value_and_milestones(self):
		job = make_contracted_job(20000)
		self.assertEqual(self.totals(job), (0, 20000))
		vo = self.approve(self.raise_order(job, 800))
		self.assertEqual((vo.contract_value_before, vo.contract_value_after), (20000, 20800))
		self.assertEqual(vo.approved_by, OTHER_PROJECT_MANAGER)
		self.approve(self.raise_order(job, 1500), user=GENERAL_MANAGER)
		self.assertEqual(self.totals(job), (2300, 22300))
		self.assertEqual(self.milestones(job), [8920, 13380])  # 40 % / 60 % of 22,300

	def test_amount_must_be_positive(self):
		job = make_contracted_job()
		for amount in (0, -10):
			with self.subTest(amount=amount), self.assertRaises(frappe.ValidationError):
				self.raise_order(job, amount)

	def test_second_person_must_approve(self):
		vo = self.raise_order(make_contracted_job())
		with self.assertRaises(frappe.PermissionError):
			self.approve(vo, user=PROJECT_MANAGER)

	def test_limit_1000(self):
		job = make_contracted_job()
		self.approve(self.raise_order(job, 1000))  # a second Project Manager, up to 1,000
		above = self.raise_order(job, 1000.01)
		with self.assertRaises(frappe.PermissionError):
			self.approve(above)
		self.approve(above, user=GENERAL_MANAGER)
		self.assertEqual(self.totals(job), (2000.01, 22000.01))

	def test_general_manager_approves_small_orders_too(self):
		job = make_contracted_job()
		self.approve(self.raise_order(job, 300), user=GENERAL_MANAGER)
		self.assertEqual(self.totals(job), (300, 20300))

	def test_inspector_cannot_approve(self):
		with self.assertRaises(frappe.PermissionError):
			self.approve(self.raise_order(make_contracted_job()), user=INSPECTOR)

	def test_client_approval_required(self):
		job = make_contracted_job()
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job, attach=False))
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job, client_approved_by=""))
		with self.assertRaises(frappe.ValidationError):
			self.raise_order(job, client_approved_on=add_days(today(), 1))

	def test_client_approval_must_be_private_and_own(self):
		job = make_contracted_job()
		vo = self.raise_order(job, attach=False)
		with as_user(PROJECT_MANAGER):
			vo.client_approval_document = private_file(
				name="public.pdf", attached_to=vo, field="client_approval_document", is_private=0
			)
			vo.save()
		with self.assertRaises(frappe.ValidationError):
			self.approve(vo)
		other = self.raise_order(job)
		borrowed = self.raise_order(job, attach=False)
		with as_user(PROJECT_MANAGER):
			borrowed.client_approval_document = other.client_approval_document
			borrowed.save()
		with self.assertRaises(frappe.ValidationError):
			self.approve(borrowed)

	def test_job_needs_approved_contract(self):
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(make_job(status="Contracted")))
		job = make_contracted_job()
		frappe.db.set_value(JOB, job.name, "status", "Closed")
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job))

	def test_cancel_restores_value_with_same_approval_rule(self):
		job = make_contracted_job()
		big = self.approve(self.raise_order(job, 5000), user=GENERAL_MANAGER)
		with as_user(OTHER_PROJECT_MANAGER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(VO, big.name).cancel()
		with as_user(GENERAL_MANAGER):
			frappe.get_doc(VO, big.name).cancel()
		self.assertEqual(self.totals(job), (0, 20000))
		self.assertEqual(self.milestones(job), [8000, 12000])

	def test_boq_revision_must_belong_to_job(self):
		job = make_contracted_job(boq=[{"description": "Wall", "qty": 10, "rate": 50}])
		rev = frappe.get_doc({"doctype": "Sidra BOQ Revision", "job": job.name, "reason": "Wall"}).insert(
			ignore_permissions=True
		)
		with self.assertRaises(frappe.ValidationError):
			self.raise_order(job, boq_revision=rev.name)  # draft, not approved
		rev.boq[0].qty = 12
		rev.save(ignore_permissions=True)
		rev.submit()
		self.assertEqual(self.raise_order(job, boq_revision=rev.name).boq_revision, rev.name)
		with self.assertRaises(frappe.ValidationError):
			self.raise_order(make_contracted_job(), boq_revision=rev.name)
