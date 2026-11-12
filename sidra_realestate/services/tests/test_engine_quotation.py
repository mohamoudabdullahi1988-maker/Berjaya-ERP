"""Pure tests for the sale quotation rules (SAL-05; decision G13). No Frappe needed."""

import unittest
from decimal import Decimal

from sidra_realestate.services.quotation import (
	GENERAL_MANAGER,
	NO_APPROVAL,
	SALES_MANAGER,
	QuotationRuleError,
	approval_level,
	approval_problem,
	check_unit_prices,
	months_problem,
)

D = Decimal
SM = [SALES_MANAGER]
GM = [GENERAL_MANAGER]


class TestUnitPrices(unittest.TestCase):
	def test_listed_price_and_discount(self):
		self.assertEqual(check_unit_prices(11000, 11000, 11000), D("0.00"))
		self.assertEqual(check_unit_prices(11000, 10450, 12000), D("550.00"))

	def test_listed_price_required(self):
		for listed in (0, None):
			with self.assertRaises(QuotationRuleError):
				check_unit_prices(listed, 100, 100)

	def test_cash_not_above_listed_or_zero(self):
		for cash in (11000.01, 0, -5):
			with self.assertRaises(QuotationRuleError):
				check_unit_prices(11000, cash, 11000)

	def test_installment_not_below_listed(self):
		with self.assertRaises(QuotationRuleError):
			check_unit_prices(11000, 11000, 10999.99)


class TestApprovalLevel(unittest.TestCase):
	def test_no_discount(self):
		self.assertEqual(approval_level([(11000, 11000), (5500, 5500)]), NO_APPROVAL)

	def test_five_percent_is_the_sales_managers_limit(self):
		self.assertEqual(approval_level([(11000, 10450)]), SALES_MANAGER)  # exactly 5 %
		self.assertEqual(approval_level([(11000, "10449.99")]), GENERAL_MANAGER)
		self.assertEqual(approval_level([(11000, "10999.99")]), SALES_MANAGER)

	def test_measured_per_unit(self):
		# 4 % overall, but one unit is discounted 8 %
		self.assertEqual(approval_level([(10000, 10000), (10000, 9200)]), GENERAL_MANAGER)


class TestApprover(unittest.TestCase):
	def test_second_person(self):
		self.assertIn("second person", approval_problem(SALES_MANAGER, "a@x", SM, "a@x"))

	def test_levels(self):
		self.assertIsNone(approval_problem(SALES_MANAGER, "b@x", SM, "a@x"))
		self.assertIsNone(approval_problem(SALES_MANAGER, "b@x", GM, "a@x"))
		self.assertIsNone(approval_problem(GENERAL_MANAGER, "b@x", GM, "a@x"))
		self.assertIn("General Manager", approval_problem(GENERAL_MANAGER, "b@x", SM, "a@x"))
		self.assertIsNotNone(approval_problem(SALES_MANAGER, "b@x", ["Sidra Sales User"], "a@x"))
		self.assertIsNotNone(approval_problem(NO_APPROVAL, "b@x", GM, "a@x"))


class TestMonths(unittest.TestCase):
	def test_twelve_to_thirty_six(self):
		for months in (12, 14, 24, 36):
			self.assertIsNone(months_problem(months), months)
		for months in (11, 37, 0, None, 12.5):
			self.assertIsNotNone(months_problem(months), months)


if __name__ == "__main__":
	unittest.main()
