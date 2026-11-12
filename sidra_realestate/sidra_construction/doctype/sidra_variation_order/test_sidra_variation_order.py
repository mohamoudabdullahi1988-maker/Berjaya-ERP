# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Variation orders (CON-06; docs/CONSTRUCTION-CONTROLS_v0.1.md §3)."""

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
	make_job,
	private_file,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Construction Job", "Customer", "Company", "User", "UOM"]

JOB = "Sidra Construction Job"


class TestSidraVariationOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def contracted_job(self, **values):
		return make_job(status="Contracted", contract_value=20000, **values)

	def raise_order(self, job, variation_type="Addition", amount=1500, attach=True, **values):
		"""Raised by the Project Manager with the client's approval recorded, as staff do."""
		with as_user(PROJECT_MANAGER):
			vo = frappe.get_doc(
				{
					"doctype": "Sidra Variation Order",
					"job": job.name,
					"variation_type": variation_type,
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
			doc = frappe.get_doc("Sidra Variation Order", vo.name)
			doc.submit()
		return doc

	def totals(self, job):
		return tuple(frappe.db.get_value(JOB, job.name, ["approved_variations", "current_contract_value"]))

	def test_addition_and_omission_change_contract_value(self):
		job = self.contracted_job()
		self.assertEqual(self.totals(job), (0, 20000))
		add = self.approve(self.raise_order(job))
		self.assertEqual(
			(add.signed_amount, add.contract_value_before, add.contract_value_after), (1500, 20000, 21500)
		)
		self.assertEqual(add.approved_by, OTHER_PROJECT_MANAGER)
		self.assertEqual(self.totals(job), (1500, 21500))
		omit = self.approve(self.raise_order(job, "Omission", 400.25))
		self.assertEqual((omit.signed_amount, omit.contract_value_after), (-400.25, 21099.75))
		self.assertEqual(self.totals(job), (1099.75, 21099.75))

	def test_second_person_must_approve(self):
		vo = self.raise_order(self.contracted_job())
		with self.assertRaises(frappe.PermissionError):
			self.approve(vo, user=PROJECT_MANAGER)

	def test_general_manager_can_approve(self):
		job = self.contracted_job()
		self.approve(self.raise_order(job), user=GENERAL_MANAGER)
		self.assertEqual(self.totals(job), (1500, 21500))

	def test_inspector_cannot_approve(self):
		vo = self.raise_order(self.contracted_job())
		with self.assertRaises(frappe.PermissionError):
			self.approve(vo, user=INSPECTOR)

	def test_client_approval_required(self):
		job = self.contracted_job()
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job, attach=False))
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job, client_approved_by=""))
		with self.assertRaises(frappe.ValidationError):
			self.raise_order(job, client_approved_on=add_days(today(), 1))

	def test_client_approval_must_be_private_and_own(self):
		job = self.contracted_job()
		with as_user(PROJECT_MANAGER):
			vo = self.raise_order(job, attach=False)
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

	def test_omission_cannot_go_below_zero(self):
		job = self.contracted_job()
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(job, "Omission", 20000.01))
		self.approve(self.raise_order(job, "Omission", 20000))
		self.assertEqual(self.totals(job), (-20000, 0))

	def test_amount_must_be_positive(self):
		with self.assertRaises(frappe.ValidationError):
			self.raise_order(self.contracted_job(), amount=-10)

	def test_job_must_be_contracted_with_value(self):
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(make_job(status="Quoted", contract_value=20000)))
		with self.assertRaises(frappe.ValidationError):
			self.approve(self.raise_order(make_job(status="Contracted")))

	def test_contract_value_locked_after_approval(self):
		job = self.contracted_job()
		job.contract_value = 21000  # editable before any variation is approved
		job.save(ignore_permissions=True)
		self.approve(self.raise_order(job))
		job.reload()
		job.contract_value = 25000
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.approved_variations = 0  # a forged total is recalculated on save
		job.save(ignore_permissions=True)
		self.assertEqual(self.totals(job), (1500, 22500))

	def test_cancel_restores_value_but_not_below_zero(self):
		job = self.contracted_job()
		add = self.approve(self.raise_order(job, amount=5000))
		self.approve(self.raise_order(job, "Omission", 24000))
		self.assertEqual(self.totals(job), (-19000, 1000))
		with as_user(OTHER_PROJECT_MANAGER), self.assertRaises(frappe.ValidationError):
			frappe.get_doc("Sidra Variation Order", add.name).cancel()
		job2 = self.contracted_job()
		vo = self.approve(self.raise_order(job2))
		with as_user(OTHER_PROJECT_MANAGER):
			frappe.get_doc("Sidra Variation Order", vo.name).cancel()
		self.assertEqual(self.totals(job2), (0, 20000))

	def test_boq_revision_must_belong_to_job(self):
		job = self.contracted_job(boq=[{"description": "Wall", "qty": 10, "rate": 50}])
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
			self.raise_order(self.contracted_job(), boq_revision=rev.name)
