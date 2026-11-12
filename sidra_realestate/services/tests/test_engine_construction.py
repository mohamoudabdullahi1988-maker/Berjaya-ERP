"""Pure tests for the construction controls (CON-05, CON-06). No Frappe needed."""

import unittest
from decimal import Decimal

from sidra_realestate.services.construction import (
	ConstructionRuleError,
	billing_pct_problem,
	boq_key,
	contract_value_after,
	inspection_problems,
	milestone_amounts,
	retention_problem,
	variation_amount,
	variation_approval_problem,
)

D = Decimal
PM = ["Sidra Project Manager"]
GM = ["Sidra General Manager"]


class TestVariations(unittest.TestCase):
	def test_additions_only(self):
		self.assertEqual(variation_amount(1250.505), D("1250.51"))
		for amount in (0, -5, None):
			with self.assertRaises(ConstructionRuleError):
				variation_amount(amount)

	def test_contract_value_reconciles(self):
		self.assertEqual(contract_value_after(20000, [D("1500"), D("250.25")]), D("21750.25"))
		self.assertEqual(contract_value_after(20000, [D("1500")], D("500")), D("22000.00"))

	def test_contract_value_required(self):
		with self.assertRaises(ConstructionRuleError):
			contract_value_after(0, [], D("100"))


class TestVariationApproval(unittest.TestCase):
	"""G11: second person; up to $1,000 a Project Manager or the GM, above $1,000 the GM only."""

	def test_second_person(self):
		self.assertIn("second person", variation_approval_problem(500, "a@x", GM, "a@x"))

	def test_at_and_below_limit(self):
		self.assertIsNone(variation_approval_problem(1000, "b@x", PM, "a@x"))
		self.assertIsNone(variation_approval_problem("999.99", "b@x", GM, "a@x"))
		self.assertIsNotNone(variation_approval_problem(500, "b@x", ["Sidra Inspector"], "a@x"))

	def test_above_limit_needs_gm(self):
		self.assertIn("General Manager", variation_approval_problem("1000.01", "b@x", PM, "a@x"))
		self.assertIsNone(variation_approval_problem(25000, "b@x", GM, "a@x"))


class TestMilestones(unittest.TestCase):
	def test_billing_must_total_100(self):
		self.assertIsNone(billing_pct_problem([40, 60, 0]))
		self.assertIsNone(billing_pct_problem([33.33, 33.33, 33.34]))
		self.assertIsNotNone(billing_pct_problem([40, 50]))
		self.assertIsNotNone(billing_pct_problem([]))

	def test_amounts_add_up_to_contract_value(self):
		amounts = milestone_amounts(1000, [33.33, 0, 33.33, 33.34, 0])
		self.assertEqual(amounts, [D("333.30"), D("0.00"), D("333.30"), D("333.40"), D("0.00")])
		amounts = milestone_amounts("10000.01", [50, 50])
		self.assertEqual(amounts, [D("5000.01"), D("5000.00")])
		self.assertEqual(sum(amounts), D("10000.01"))

	def test_no_reconciliation_when_not_100(self):
		self.assertEqual(milestone_amounts(1000, [40, 50]), [D("400.00"), D("500.00")])


class TestRetention(unittest.TestCase):
	def test_limits(self):
		for pct, months in ((0, 0), (10, 12), (5.5, 6), (None, None)):
			self.assertIsNone(retention_problem(pct, months), (pct, months))
		for pct, months in ((10.01, 12), (-1, 0), (5, -1), (5, 1.5)):
			self.assertIsNotNone(retention_problem(pct, months), (pct, months))


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
