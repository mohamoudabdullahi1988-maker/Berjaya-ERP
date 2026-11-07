# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""The staging demonstration builds, is repeatable, and shows contract capture (CONTRACT-CAPTURE_v0.3 §6.5)."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.demo import create_demo_data
from sidra_realestate.sidra_sales.doctype.sidra_contract_import.sidra_contract_import import run_import

LEDGER_DOCTYPES = ("Sales Order", "Sales Invoice", "Payment Entry", "Journal Entry", "GL Entry")


class TestDemo(IntegrationTestCase):
	def test_demo_builds_and_is_repeatable(self):
		frappe.conf.sidra_allow_demo_data = 1
		self.addCleanup(frappe.conf.pop, "sidra_allow_demo_data", None)

		first = create_demo_data()
		before = {dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}
		second = create_demo_data()
		self.assertEqual(first["registered_contracts"], second["registered_contracts"])
		self.assertEqual({dt: frappe.db.count(dt) for dt in LEDGER_DOCTYPES}, before)

		contracts = first["registered_contracts"]
		state = {
			ref: frappe.db.get_value(
				"Sidra Sale Contract",
				name,
				["docstatus", "schedule_difference", "terms_approved_by", "terms_snapshot"],
				as_dict=True,
			)
			for ref, name in contracts.items()
		}
		self.assertEqual(
			{ref: s.docstatus for ref, s in state.items()},
			{
				"EXT-DEMO-0001": 1,
				"EXT-DEMO-0002": 1,
				"EXT-DEMO-0003": 0,  # $10 difference: over the $5 limit, stays a draft
				"EXT-DEMO-0004": 1,
				"EXT-DEMO-0005": 1,
				"EXT-DEMO-0006": 1,
			},
		)
		self.assertEqual(state["EXT-DEMO-0002"].schedule_difference, 4)
		self.assertEqual(state["EXT-DEMO-0003"].schedule_difference, 10)
		self.assertEqual(state["EXT-DEMO-0001"].terms_approved_by, "demo.manager@example.com")
		self.assertEqual(json.loads(state["EXT-DEMO-0004"].terms_snapshot)["title_penalty_amount"], 220)
		self.assertEqual(frappe.db.count("Sidra Installment Line", {"parent": contracts["EXT-DEMO-0001"]}), 7)

		# The sample migration file imports cleanly onto the demo's migration plots (G5).
		path = frappe.get_app_path("sidra_realestate", "public", "templates", "sample_live_contracts.csv")
		with open(path, "rb") as fh:
			content = fh.read()
		file_doc = frappe.get_doc(
			{"doctype": "File", "file_name": "sample_live_contracts.csv", "content": content, "is_private": 1}
		).insert(ignore_permissions=True)
		job = frappe.get_doc(
			{
				"doctype": "Sidra Contract Import",
				"company": first["company"],
				"import_file": file_doc.file_url,
				"create_missing_customers": 1,
			}
		).insert(ignore_permissions=True)
		result = run_import(job.name)
		self.assertEqual(result["status"], "Imported", result["log"])
		self.assertEqual(frappe.db.get_value("Sidra Contract Import", job.name, "contracts_created"), 8)
		mig = frappe.db.get_value("Sidra Sale Contract", {"external_reference": "MIG-0005"}, "name")
		self.assertEqual(frappe.db.count("Sidra Installment Line", {"parent": mig}), 36)
