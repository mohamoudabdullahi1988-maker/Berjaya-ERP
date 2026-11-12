"""Pure tests for the construction controls (CON-05, CON-06). No Frappe needed."""

import unittest
from decimal import Decimal

from sidra_realestate.services.construction import (
	ConstructionRuleError,
	boq_key,
	contract_value_after,
	inspection_problems,
	signed_variation,
)

D = Decimal


class TestVariations(unittest.TestCase):
	def test_addition_and_omission_signs(self):
		self.assertEqual(signed_variation("Addition", 1250.505), D("1250.51"))
		self.assertEqual(signed_variation("Omission", "300"), D("-300.00"))

	def test_amount_must_be_positive(self):
		for amount in (0, -5, None):
			with self.assertRaises(ConstructionRuleError):
				signed_variation("Addition", amount)
		with self.assertRaises(ConstructionRuleError):
			signed_variation("Discount", 10)

	def test_contract_value_reconciles(self):
		self.assertEqual(contract_value_after(20000, [D("1500"), D("-250.25")]), D("21249.75"))
		self.assertEqual(contract_value_after(20000, [D("1500")], D("-500")), D("21000.00"))

	def test_contract_value_cannot_go_negative(self):
		self.assertEqual(contract_value_after(1000, [], D("-1000")), D("0.00"))
		with self.assertRaises(ConstructionRuleError):
			contract_value_after(1000, [D("-600")], D("-400.01"))

	def test_contract_value_required(self):
		with self.assertRaises(ConstructionRuleError):
			contract_value_after(0, [], D("100"))


class TestBoqKey(unittest.TestCase):
	def test_same_content_same_key(self):
		a = [{"cost_code": "01 ", "description": "Excavation", "uom": "m3", "qty": 12.50, "rate": 8}]
		b = [{"cost_code": "01", "description": "Excavation ", "uom": "m3", "qty": "12.5", "rate": "8.00"}]
		self.assertEqual(boq_key(a), boq_key(b))

	def test_change_detected(self):
		a = [{"description": "Excavation", "qty": 12.5, "rate": 8}]
		self.assertNotEqual(boq_key(a), boq_key([{"description": "Excavation", "qty": 12.5, "rate": 8.01}]))
		self.assertNotEqual(boq_key(a), boq_key(a + a))
		self.assertNotEqual(boq_key(a + [{"description": "B"}]), boq_key([{"description": "B"}] + a))


class TestInspection(unittest.TestCase):
	def test_consistent_pass(self):
		checks = [{"item": "Rebar spacing", "result": "Pass"}, {"item": "Cover", "result": "Not Applicable"}]
		self.assertEqual(inspection_problems("Pass", checks), [])

	def test_failed_row_needs_remarks_and_blocks_pass(self):
		problems = inspection_problems("Pass", [{"item": "Cover", "result": "Fail"}])
		self.assertEqual(len(problems), 2)

	def test_defects_need_description_and_next_action(self):
		checks = [{"item": "Cover", "result": "Fail", "remarks": "15 mm, needs 25 mm"}]
		self.assertEqual(len(inspection_problems("Fail", checks)), 2)
		self.assertEqual(inspection_problems("Fail", checks, "Low cover on slab edge", "Re-pour edge"), [])
		self.assertEqual(
			inspection_problems("Pass with defects", [], "Hairline cracks", "Monitor at next visit"), []
		)

	def test_unknown_values(self):
		self.assertEqual(len(inspection_problems("Maybe", [{"item": "x", "result": "?"}])), 2)


if __name__ == "__main__":
	unittest.main()
