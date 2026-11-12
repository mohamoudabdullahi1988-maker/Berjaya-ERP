import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.desk_setup import repair_desk, scheme_summary
from sidra_realestate.tests.helpers import OUTSIDER, as_user, ensure_base_records, make_scheme, make_unit, unique


class TestDeskUI(IntegrationTestCase):
	def setUp(self):
		ensure_base_records()

	def test_counts_follow_unit_status(self):
		scheme = make_scheme(unique("_Test UI"))
		make_unit(unique("_Test UI Unit"), scheme)
		make_unit(unique("_Test UI Blocked"), scheme, status="Blocked")
		data = scheme_summary([scheme])[scheme]
		self.assertEqual(data["total"], 2)
		self.assertEqual(data["available"], 1)

	def test_outsider_cannot_fetch_scheme_summary(self):
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			scheme_summary(["private-scheme"])

	def test_unit_presentation_and_location_source(self):
		meta = frappe.get_meta("Sidra Unit")
		self.assertIn("House", meta.get_field("section_house").depends_on)
		self.assertEqual(meta.get_field("district").fetch_from, "scheme.district")
		self.assertTrue(meta.get_field("cash_price").in_list_view)
		self.assertFalse(meta.get_field("current_contract").hidden)

	def test_child_grid_fits_ten_columns(self):
		fields = frappe.get_meta("Sidra Installment Line").fields
		self.assertEqual(sum(f.columns for f in fields if f.in_list_view), 10)
		self.assertFalse(next(f for f in fields if f.fieldname == "description").in_list_view)

	def test_presentation_labels_have_no_requirement_ids(self):
		for dt in ("Sidra Unit", "Sidra Sale Contract", "Sidra Contract Profile", "Sidra Contract Settings"):
			for field in frappe.get_meta(dt).fields:
				for value in (field.label, field.description):
					self.assertNotRegex(value or "", r"\b(?:SAL|INS|CC|NFR)-\d+")

	def test_repair_is_idempotent(self):
		repair_desk()
		repair_desk()
