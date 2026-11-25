# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G41: a store (ERPNext Warehouse) per house; ledger-posting moves wait for Finance."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.services.construction_projects import create_project, ensure_project_fields
from sidra_realestate.services.construction_stores import (
	GROUP,
	backfill_site_stores,
	create_site_store,
	ensure_store_fields,
	refuse_site_stock_move,
)
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_job,
)

JOB = "Sidra Construction Job"
BRICK = "_Test Site Brick"


class TestConstructionStores(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_project_fields()
		ensure_store_fields()
		if not frappe.db.exists("Item", BRICK):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": BRICK,
					"item_group": "All Item Groups",
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			).insert(ignore_permissions=True)

	def job(self, **values):
		job = make_job(plot_number="_Test plot 9", **values)
		for i, row in enumerate(job.stages):
			row.planned_start = add_days(today(), i * 10)
			row.planned_end = add_days(today(), i * 10 + 9)
		job.save(ignore_permissions=True)
		return job

	def test_the_project_brings_the_house_store(self):
		job = self.job()
		with as_user(PROJECT_MANAGER):
			result = create_project(job.name)
		store = result["warehouse"]
		self.assertEqual(frappe.db.get_value(JOB, job.name, "warehouse"), store)
		values = frappe.db.get_value(
			"Warehouse",
			store,
			["company", "is_group", "sidra_construction_job", "parent_warehouse"],
			as_dict=True,
		)
		self.assertEqual(
			(values.company, values.is_group, values.sidra_construction_job), (COMPANY, 0, job.name)
		)
		self.assertEqual(frappe.db.get_value("Warehouse", values.parent_warehouse, "warehouse_name"), GROUP)

	def test_a_store_for_a_job_that_has_a_project(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test store project",
				"company": COMPANY,
				"customer": BUYER,
			}
		).insert(ignore_permissions=True)
		job = self.job(project=project.name)
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			create_site_store(job.name)
		with as_user(PROJECT_MANAGER):
			store = create_site_store(job.name)["warehouse"]
			with self.assertRaises(frappe.ValidationError):
				create_site_store(job.name)
		self.assertEqual(frappe.db.get_value("Warehouse", store, "sidra_construction_job"), job.name)

	def test_material_requests_yes_stock_moves_not_yet(self):
		job = self.job()
		with as_user(PROJECT_MANAGER):
			store = create_project(job.name)["warehouse"]
		request = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": COMPANY,
				"schedule_date": add_days(today(), 7),
				"set_warehouse": store,
				"items": [
					{
						"item_code": BRICK,
						"qty": 500,
						"schedule_date": add_days(today(), 7),
						"warehouse": store,
					}
				],
			}
		).insert(ignore_permissions=True)
		request.submit()
		self.assertEqual(request.docstatus, 1)

		receipt = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": COMPANY,
				"items": [{"item_code": BRICK, "qty": 10, "basic_rate": 1, "t_warehouse": store}],
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "G41"):
			refuse_site_stock_move(receipt)

		other = frappe.db.get_value(
			"Warehouse",
			{"company": COMPANY, "is_group": 0, "sidra_construction_job": ["is", "not set"]},
			"name",
		)
		refuse_site_stock_move(
			frappe._dict(doctype="Stock Entry", items=[frappe._dict(t_warehouse=other)])
		)  # other stores are not affected
		refuse_site_stock_move(
			frappe._dict(doctype="Purchase Invoice", update_stock=0, items=[frappe._dict(warehouse=store)])
		)  # an invoice that moves no stock is not affected

	def test_backfill_gives_linked_jobs_their_store(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test backfill project",
				"company": COMPANY,
				"customer": BUYER,
			}
		).insert(ignore_permissions=True)
		job = self.job(project=project.name)
		with as_user("Administrator"):
			made = backfill_site_stores(company=COMPANY)
			self.assertIn(job.name, made)
			self.assertNotIn(job.name, backfill_site_stores(company=COMPANY))
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			backfill_site_stores()
