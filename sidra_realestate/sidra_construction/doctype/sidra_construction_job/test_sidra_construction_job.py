# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Construction job (CON-01, CON-02, CON-04 partial; SRS v2.0 §3.1; handoff checklist)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_BUYER,
	OTHER_COMPANY,
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
		self.assertEqual([s.stage_name for s in self.job(service_type="Inspection Only").stages][0], "Request")
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
