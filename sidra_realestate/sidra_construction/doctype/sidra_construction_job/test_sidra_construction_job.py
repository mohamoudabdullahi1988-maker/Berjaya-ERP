# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Construction job (CON-01, CON-02, CON-04 partial; SRS v2.0 §3.1; handoff checklist)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.sidra_construction.doctype.sidra_construction_job.sidra_construction_job import (
	certify_stage,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	INSPECTOR,
	OTHER_BUYER,
	OTHER_COMPANY,
	PROJECT_MANAGER,
	as_user,
	ensure_base_records,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Customer", "Company", "User", "UOM"]


class TestSidraConstructionJob(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def job(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"customer": BUYER,
				"company": COMPANY,
				"service_type": "Full Construction",
				**values,
			}
		).insert(ignore_permissions=True)

	def project(self, company=COMPANY, customer=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": unique("_Test Sidra Project"),
					"company": company,
					"customer": customer,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_boq_totals(self):
		doc = self.job(
			boq=[
				{"description": "Excavation", "cost_code": "01", "qty": 12.5, "rate": 8},
				{"description": "Concrete", "cost_code": "02", "qty": 3, "rate": 145.555},
				{"description": "Rebar", "cost_code": "03", "qty": 0, "rate": 900},
			]
		)
		self.assertEqual([row.amount for row in doc.boq], [100.0, 436.67, 0.0])
		self.assertEqual(doc.boq_total, 536.67)

	def test_negative_boq_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.job(boq=[{"description": "Credit", "qty": -1, "rate": 10}])

	def test_stage_template_copied(self):
		self.assertEqual(len(self.job().stages), 9)
		self.assertEqual(
			[s.stage_name for s in self.job(service_type="Inspection Only").stages][0], "Request"
		)
		self.assertEqual(self.job(service_type="Beacon / Foundation").stages, [])
		custom = self.job(stages=[{"stage_name": "Only stage"}])
		self.assertEqual([s.stage_name for s in custom.stages], ["Only stage"])

	def test_stage_percentages_and_dates(self):
		with self.assertRaises(frappe.ValidationError):
			self.job(stages=[{"stage_name": "A", "billing_pct": 60}, {"stage_name": "B", "billing_pct": 50}])
		with self.assertRaises(frappe.ValidationError):
			self.job(stages=[{"stage_name": "A", "completion_pct": 120}])
		with self.assertRaises(frappe.ValidationError):
			self.job(stages=[{"stage_name": "A", "planned_start": "2026-12-01", "planned_end": "2026-11-01"}])

	def test_project_must_match_company(self):
		self.assertTrue(self.job(project=self.project()))
		with self.assertRaises(frappe.ValidationError):
			self.job(project=self.project(company=OTHER_COMPANY))

	def test_project_must_match_customer(self):
		with self.assertRaises(frappe.ValidationError):
			self.job(project=self.project(customer=OTHER_BUYER))


class TestStageCertification(IntegrationTestCase):
	"""CON-04: the Project Manager certifies completed stages (docs/CONSTRUCTION-CONTROLS_v0.2.md §5)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def job(self, **stage):
		values = {
			"stage_name": "Foundation",
			"status": "Completed",
			"completion_pct": 100,
			"actual_start": add_days(today(), -20),
			"actual_end": add_days(today(), -1),
			"billing_pct": 20,
			**stage,
		}
		return frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"customer": BUYER,
				"company": COMPANY,
				"service_type": "Full Construction",
				"status": "In Progress",
				"stages": [values, {"stage_name": "Structure"}],
			}
		).insert(ignore_permissions=True)

	def certify(self, job, row=0, user=PROJECT_MANAGER):
		with as_user(user):
			return certify_stage(job.name, job.stages[row].name)

	def test_project_manager_certifies(self):
		job = self.job()
		result = self.certify(job)
		job.reload()
		stage = job.stages[0]
		self.assertEqual((stage.certified, stage.certified_by), (1, PROJECT_MANAGER))
		self.assertTrue(stage.certified_on)
		self.assertEqual(result["certified_by"], PROJECT_MANAGER)
		with self.assertRaises(frappe.ValidationError):
			self.certify(job)  # already certified

	def test_only_complete_past_stages(self):
		for stage in (
			{"status": "In Progress"},
			{"completion_pct": 90},
			{"actual_end": None},
			{"actual_end": add_days(today(), 2), "actual_start": today()},
		):
			with self.subTest(stage=stage), self.assertRaises(frappe.ValidationError):
				self.certify(self.job(**stage))

	def test_inspector_cannot_certify(self):
		with self.assertRaises(frappe.PermissionError):
			self.certify(self.job(), user=INSPECTOR)

	def test_cancelled_job_refused(self):
		job = self.job()
		frappe.db.set_value("Sidra Construction Job", job.name, "status", "Cancelled")
		with self.assertRaises(frappe.ValidationError):
			self.certify(job)

	def test_certified_stage_frozen(self):
		job = self.job()
		self.certify(job)
		job.reload()
		job.stages[0].billing_pct = 30
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.remove(job.stages[0])
		with self.assertRaises(frappe.ValidationError):
			job.save(ignore_permissions=True)
		job.reload()
		job.stages[1].status = "In Progress"  # other stages stay editable
		job.save(ignore_permissions=True)
		self.assertEqual(job.stages[0].certified, 1)

	def test_certification_cannot_be_forged(self):
		job = self.job()
		job.stages[0].certified = 1
		job.stages[0].certified_by = PROJECT_MANAGER
		job.save(ignore_permissions=True)
		job.reload()
		self.assertEqual((job.stages[0].certified, job.stages[0].certified_by), (0, None))
		forged = self.job(certified=1, certified_by=PROJECT_MANAGER)
		self.assertEqual(forged.stages[0].certified, 0)


class TestContractValue(IntegrationTestCase):
	"""CON-03 / G11: contract terms come only from an approved quotation, never typed on the job."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_contract_value_cannot_be_typed(self):
		job = frappe.get_doc(
			{
				"doctype": "Sidra Construction Job",
				"customer": BUYER,
				"company": COMPANY,
				"service_type": "Design Only",
				"contract_value": 4500,
				"approved_variations": 999,
				"retention_pct": 10,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(
			(
				job.contract_value or 0,
				job.approved_variations,
				job.current_contract_value,
				job.retention_pct or 0,
			),
			(0, 0, 0, 0),
		)
		job.contract_value = 4500
		job.save(ignore_permissions=True)
		self.assertEqual(job.contract_value or 0, 0)
