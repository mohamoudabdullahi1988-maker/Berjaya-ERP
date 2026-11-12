# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Construction quotation and contract (CON-02, CON-03; decision G11; docs/CONSTRUCTION-CONTROLS_v0.2.md §3)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.sidra_construction.doctype.sidra_construction_quotation.sidra_construction_quotation import (
	approve_contract,
)
from sidra_realestate.tests.helpers import (
	GENERAL_MANAGER,
	PROJECT_MANAGER,
	as_user,
	ensure_base_records,
	issue_quotation,
	make_contracted_job,
	make_job,
	private_file,
	record_acceptance,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Construction Job", "Customer", "Company", "User", "UOM"]

JOB = "Sidra Construction Job"
QUOTATION = "Sidra Construction Quotation"
MILESTONES = [{"stage_name": "Foundation", "billing_pct": 40}, {"stage_name": "Structure", "billing_pct": 60}]
BOQ = [
	{"cost_code": "01", "description": "Excavation", "qty": 12.5, "rate": 8},
	{"cost_code": "02", "description": "Concrete", "qty": 3, "rate": 145},
]


class TestSidraConstructionQuotation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def draft(self, job, **values):
		return frappe.get_doc(
			{
				"doctype": QUOTATION,
				"job": job.name,
				"pricing_basis": "BOQ",
				"scope": "Foundation works",
				"valid_until": add_days(today(), 30),
				"start_date": add_days(today(), 7),
				"duration_days": 30,
				**values,
			}
		).insert(ignore_permissions=True)

	def approve(self, quotation, user=GENERAL_MANAGER):
		with as_user(user):
			return approve_contract(quotation.name)

	# ------------------------------------------------------------ CON-02 quotation
	def test_boq_quotation_freezes_job_boq(self):
		job = make_job(boq=BOQ)
		q = self.draft(job)
		self.assertEqual((q.boq_total, q.quoted_amount, q.fixed_fee), (535, 535, 0))
		self.assertEqual(getdate(q.end_date), getdate(add_days(today(), 36)))
		q.submit()
		self.assertEqual(q.status, "Issued")
		self.assertEqual(frappe.db.get_value(JOB, job.name, "status"), "Quoted")

	def test_fixed_fee_quotation(self):
		job = make_job(service_type="Inspection Only", boq=BOQ)
		q = self.draft(job, pricing_basis="Fixed Fee", fixed_fee=350)
		self.assertEqual((q.quoted_amount, q.boq_total, len(q.boq)), (350, 0, 0))
		with self.assertRaises(frappe.ValidationError):
			self.draft(job, pricing_basis="Fixed Fee", fixed_fee=0)
		with self.assertRaises(frappe.ValidationError):
			self.draft(make_job())  # BOQ basis without a BOQ

	def test_stale_boq_refused_at_issue(self):
		job = make_job(boq=BOQ)
		q = self.draft(job)
		job.reload()
		job.boq[0].rate = 9
		job.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			q.submit()

	def test_expired_quotation_refused_at_issue(self):
		job = make_job(boq=BOQ)
		q = self.draft(job, valid_until=add_days(today(), -1))
		with self.assertRaises(frappe.ValidationError):
			q.submit()

	def test_terms_checked(self):
		job = make_job(boq=BOQ)
		for values in (
			{"retention_pct": 10.5},
			{"retention_period_months": -1},
			{"duration_days": 0},
			{"scope": " "},
		):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				self.draft(job, **values)
		self.assertEqual(self.draft(job, retention_pct=10).retention_pct, 10)

	# ------------------------------------------------------------ CON-03 contract
	def test_general_manager_approves_contract(self):
		job = make_job(stages=MILESTONES, boq=BOQ)
		q = record_acceptance(issue_quotation(job, 20000))
		result = self.approve(q)
		job.reload()
		self.assertEqual(result["contract_value"], 20000)
		self.assertEqual(
			(job.contract_quotation, job.contract_value, job.current_contract_value, job.status),
			(q.name, 20000, 20000, "Contracted"),
		)
		self.assertEqual(
			(job.retention_pct, job.retention_period_months, job.contract_duration_days), (5, 12, 120)
		)
		self.assertEqual(getdate(job.contract_end_date), getdate(q.end_date))
		self.assertEqual(job.contract_approved_by, GENERAL_MANAGER)
		self.assertEqual([s.billing_amount for s in job.stages], [8000, 12000])
		q.reload()
		self.assertEqual((q.status, q.contract_approved_by), ("Contracted", GENERAL_MANAGER))

	def test_only_general_manager_approves(self):
		q = record_acceptance(issue_quotation(make_job(stages=MILESTONES)))
		with self.assertRaises(frappe.PermissionError):
			self.approve(q, user=PROJECT_MANAGER)

	def test_acceptance_required_and_private(self):
		job = make_job(stages=MILESTONES)
		with self.assertRaises(frappe.ValidationError):
			self.approve(issue_quotation(job))
		with self.assertRaises(frappe.ValidationError):
			self.approve(record_acceptance(issue_quotation(job), is_private=0))

	def test_acceptance_after_expiry_refused(self):
		q = issue_quotation(make_job(stages=MILESTONES), valid_until=today())
		q.client_accepted_on = add_days(today(), 1)
		with self.assertRaises(frappe.ValidationError):
			q.save(ignore_permissions=True)  # also in the future

	def test_milestones_must_total_100(self):
		job = make_job(stages=[{"stage_name": "Foundation", "billing_pct": 40}])
		with self.assertRaises(frappe.ValidationError):
			self.approve(record_acceptance(issue_quotation(job)))
		self.assertFalse(frappe.db.get_value(JOB, job.name, "contract_quotation"))

	def test_one_contract_per_job(self):
		job = make_job(stages=MILESTONES)
		first = record_acceptance(issue_quotation(job))
		second = record_acceptance(issue_quotation(job, 21000))
		self.approve(first)
		with self.assertRaises(frappe.ValidationError):
			self.approve(second)
		with self.assertRaises(frappe.ValidationError):
			self.approve(first)
		with self.assertRaises(frappe.ValidationError):
			issue_quotation(frappe.get_doc(JOB, job.name))  # no new quotation once contracted

	def test_contract_terms_locked_on_job(self):
		job = make_contracted_job(20000)
		job.contract_value = 99999
		job.retention_pct = 0
		job.contract_quotation = None
		job.save(ignore_permissions=True)
		job.reload()
		self.assertEqual(
			(job.contract_value, job.retention_pct, bool(job.contract_quotation)), (20000, 5, True)
		)
		forged = make_job(contract_value=5000, contract_quotation=job.contract_quotation)
		self.assertEqual(
			(forged.contract_value or 0, forged.contract_quotation, forged.current_contract_value),
			(0, None, 0),
		)

	def test_milestones_locked_after_contract(self):
		job = make_contracted_job()
		job.stages[0].billing_pct = 50
		job.stages[1].billing_pct = 50
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.append("stages", {"stage_name": "Snagging"})  # an unbilled stage can still be added
		job.save(ignore_permissions=True)
		job.reload()
		job.remove(job.stages[0])
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)

	def test_contracted_quotation_cannot_be_cancelled_or_reaccepted(self):
		job = make_contracted_job()
		q = frappe.get_doc(QUOTATION, job.contract_quotation)
		q.client_accepted_by = "Someone else"
		with self.assertRaises(frappe.ValidationError):
			q.save(ignore_permissions=True)
		q.reload()
		with self.assertRaises(frappe.ValidationError):
			q.cancel()

	def test_uncontracted_quotation_can_be_cancelled(self):
		q = issue_quotation(make_job(stages=MILESTONES))
		q.cancel()
		self.assertEqual(frappe.db.get_value(QUOTATION, q.name, "status"), "Cancelled")

	def test_acceptance_file_must_be_own(self):
		job = make_job(stages=MILESTONES)
		other = record_acceptance(issue_quotation(job))
		q = issue_quotation(job)
		q.client_accepted_by = "_Test Buyer Amina"
		q.client_accepted_on = today()
		q.client_acceptance_document = other.client_acceptance_document
		q.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.approve(q)
		q.reload()
		q.client_acceptance_document = private_file(
			name="own.pdf", attached_to=q, field="client_acceptance_document"
		)
		q.save(ignore_permissions=True)
		self.approve(q)

	def test_print_on_letterhead(self):
		job = make_job(stages=MILESTONES, boq=BOQ)
		q = self.draft(job)
		html = frappe.get_print(QUOTATION, q.name, print_format="Sidra Construction Quotation", doc=q)
		self.assertIn("sidra-logo.png", html)
		self.assertIn(q.name, html)
		self.assertIn("Excavation", html)
		self.assertIn("Draft", html)
		self.assertIn("Foundation", html)
