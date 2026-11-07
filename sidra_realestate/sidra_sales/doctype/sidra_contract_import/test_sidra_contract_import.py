# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Contract import from a spreadsheet (decision G5; D8)."""

from datetime import date
from io import BytesIO

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.sidra_sales.doctype.sidra_contract_import.sidra_contract_import import (
	run_import,
	validate_import,
)
from sidra_realestate.tests.helpers import BUYER, COMPANY, ensure_base_records, make_scheme, make_unit, unique

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "User", "Customer", "Sidra Unit", "Sidra Sale Contract"]

HEADER = "external_reference,customer,signed_on,agreed_price,unit,unit_price,down_payment_mode,down_payment,row_type,due_date,amount"


class TestContractImport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		cls.scheme = make_scheme("_TEST-IMP")

	def unit(self):
		return make_unit(unique("_T-IMP"), self.scheme).name

	def importer(self, content, name="contracts.csv", **values):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{frappe.generate_hash(length=6)}-{name}",
				"content": content,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "Sidra Contract Import",
				"company": COMPANY,
				"import_file": file_doc.file_url,
				**values,
			}
		).insert(ignore_permissions=True)

	def two_contracts(self):
		u1, u2, u3 = self.unit(), self.unit(), self.unit()
		r1, r2 = unique("EXT-IMP"), unique("EXT-IMP")
		lines = [
			HEADER,
			f"{r1},{BUYER},15/01/2026,9000,{u1},9000,Recorded separately,3000,Installment,10/04/2026,3000",
			f"{r1},,,,{u1},,,,Installment,10/05/2026,3000",
			f"{r1},,,,{u1},,,,Fee,2026-06-10,0.01",
			f"{r2},{BUYER},2025-03-01,10000,{u2},5000,,,Installment,2025-03-01,5000",
			f"{r2},,,,{u3},5000,,,Installment,2025-03-01,5000",
		]
		return "\n".join(lines), (r1, r2)

	def contracts(self, *refs):
		return {
			r: frappe.db.get_value("Sidra Sale Contract", {"external_reference": r}, "name") for r in refs
		}

	def test_validate_then_import(self):
		content, refs = self.two_contracts()
		job = self.importer(content)

		result = validate_import(job.name)
		self.assertEqual(result["status"], "Validated", result["log"])
		self.assertEqual(self.contracts(*refs), {refs[0]: None, refs[1]: None})  # dry run keeps nothing

		result = run_import(job.name)
		self.assertEqual(result["status"], "Imported", result["log"])
		names = self.contracts(*refs)
		first = frappe.get_doc("Sidra Sale Contract", names[refs[0]])
		self.assertEqual((first.docstatus, first.source), (0, "External (registered)"))
		self.assertEqual((first.down_payment_mode, first.down_payment), ("Recorded separately", 3000))
		self.assertEqual(
			[(r.row_type, r.amount) for r in first.schedule],
			[("Installment", 3000), ("Installment", 3000), ("Fee", 0.01)],
		)
		self.assertEqual(getdate(first.signed_on), date(2026, 1, 15))
		self.assertEqual(first.schedule_difference, -0.01)  # shown, decided at confirmation (D3)
		second = frappe.get_doc("Sidra Sale Contract", names[refs[1]])
		self.assertEqual(len(second.units), 2)
		self.assertEqual(second.schedule_difference, 0)
		self.assertEqual(frappe.db.get_value("Sidra Contract Import", job.name, "contracts_created"), 2)

		again = run_import(self.importer(content).name)  # same file again: skipped, nothing duplicated
		self.assertIn("Skipped", again["log"])
		self.assertEqual(frappe.db.count("Sidra Sale Contract", {"external_reference": refs[0]}), 1)

	def test_one_bad_contract_blocks_the_file(self):
		content, refs = self.two_contracts()
		bad_ref = unique("EXT-IMP")
		content += f"\n{bad_ref},{BUYER},2025-03-01,1000,NO-SUCH-UNIT,,,,Installment,2025-04-01,1000"
		result = run_import(self.importer(content).name)
		self.assertEqual(result["status"], "Failed")
		self.assertIn("NO-SUCH-UNIT", result["log"])
		self.assertEqual(self.contracts(*refs, bad_ref), {refs[0]: None, refs[1]: None, bad_ref: None})

	def test_reader_errors_reported(self):
		result = validate_import(
			self.importer(f"{HEADER}\nEXT-X,{BUYER},31/02/2026,100,U,,,,,2026-04-01,100").name
		)
		self.assertEqual(result["status"], "Failed")
		self.assertIn("Row 2", result["log"])

	def test_missing_customer_created_only_when_asked(self):
		unit, ref, buyer = self.unit(), unique("EXT-IMP"), unique("_Test Imported Buyer")
		content = f"{HEADER}\n{ref},{buyer},2026-01-15,500,{unit},,,,,2026-02-10,500"
		self.assertEqual(run_import(self.importer(content).name)["status"], "Failed")
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": buyer}))
		result = run_import(self.importer(content, create_missing_customers=1).name)
		self.assertEqual(result["status"], "Imported", result["log"])
		self.assertTrue(frappe.db.exists("Customer", {"customer_name": buyer}))

	def test_xlsx_file(self):
		from openpyxl import Workbook

		unit, ref = self.unit(), unique("EXT-IMP")
		wb = Workbook()
		ws = wb.active
		ws.append(HEADER.split(","))
		ws.append([ref, BUYER, date(2026, 1, 15), 700, unit, None, None, None, None, date(2026, 2, 10), 700])
		buffer = BytesIO()
		wb.save(buffer)
		result = run_import(self.importer(buffer.getvalue(), name="contracts.xlsx").name)
		self.assertEqual(result["status"], "Imported", result["log"])
		self.assertTrue(self.contracts(ref)[ref])
