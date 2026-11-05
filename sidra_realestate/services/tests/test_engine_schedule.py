"""Pure tests for the P0 schedule generator. No Frappe needed:

	python -m unittest discover -s sidra_realestate -p "test_engine_*.py" -t .

AT-xx are the acceptance cases in docs/HANDOVER_v1.0.md §6 that fall inside P0.
AT-05 to AT-11 and AT-13 (markup, penalties, allocation, default, title) are P2.
"""

import unittest
from datetime import date
from decimal import Decimal

from sidra_realestate.services.schedule import (
	ScheduleError,
	down_payment_amount,
	first_due_date,
	generate_installments,
)

D = Decimal


class TestAcceptanceCases(unittest.TestCase):
	def test_at01_profile_a_14000(self):
		lines = generate_installments(14000, 0, 14, date(2025, 8, 31), 0, 5)
		self.assertEqual(len(lines), 14)
		self.assertEqual({line.amount for line in lines}, {D("1000.00")})
		self.assertEqual(lines[0].due_date, date(2025, 9, 5))
		self.assertEqual(lines[-1].due_date, date(2026, 10, 5))
		self.assertEqual([line.seq for line in lines], list(range(1, 15)))

	def test_at02_hagbad_full_plot(self):
		lines = generate_installments(11000, 0, 14, date(2026, 11, 5), 0, 5)
		self.assertEqual([line.amount for line in lines], [D("786.00")] * 13 + [D("782.00")])
		self.assertEqual(sum(line.amount for line in lines), D("11000.00"))

	def test_at03_profile_b_terms(self):
		# Issue #1: SRS v2.0 §3.3 wording would give 2026-05-10; AT-03 expects 2026-04-10.
		down = down_payment_amount(9000, "Fixed", 3000)
		lines = generate_installments(9000, down, 24, date(2026, 1, 15), 3, 10)
		self.assertEqual(down, D("3000.00"))
		self.assertEqual(len(lines), 24)
		self.assertEqual({line.amount for line in lines}, {D("250.00")})
		self.assertEqual(lines[0].due_date, date(2026, 4, 10))
		self.assertEqual(lines[-1].due_date, date(2028, 3, 10))

	def test_at04_hagbad_half_plot(self):
		lines = generate_installments(5500, 0, 22, date(2026, 11, 5), 0, 5)
		self.assertEqual(len(lines), 22)
		self.assertEqual({line.amount for line in lines}, {D("250.00")})


class TestFirstDueDate(unittest.TestCase):
	def test_after_due_day_moves_to_next_month(self):
		self.assertEqual(first_due_date(date(2026, 3, 6), 0, 5), date(2026, 4, 5))

	def test_before_due_day_stays_in_month(self):
		self.assertEqual(first_due_date(date(2026, 3, 2), 0, 5), date(2026, 3, 5))

	def test_signed_on_due_day_moves_to_next_month(self):
		# Open question in issue #1.
		self.assertEqual(first_due_date(date(2026, 3, 5), 0, 5), date(2026, 4, 5))

	def test_month_end_signing_has_no_rollover(self):
		for day in (29, 30, 31):
			self.assertEqual(first_due_date(date(2026, 1, day), 0, 28), date(2026, 2, 28))
		self.assertEqual(first_due_date(date(2024, 2, 29), 0, 28), date(2024, 3, 28))

	def test_grace_crosses_year(self):
		self.assertEqual(first_due_date(date(2026, 11, 20), 3, 10), date(2027, 2, 10))


class TestRoundingAndDownPayment(unittest.TestCase):
	def test_last_installment_absorbs_cents(self):
		lines = generate_installments("1000.50", 0, 3, date(2026, 1, 1), 0, 5)
		self.assertEqual([line.amount for line in lines], [D("334.00"), D("334.00"), D("332.50")])

	def test_half_dollar_rounds_up(self):
		lines = generate_installments(1001, 0, 2, date(2026, 1, 1), 0, 5)
		self.assertEqual([line.amount for line in lines], [D("501.00"), D("500.00")])

	def test_single_installment(self):
		lines = generate_installments(5000, 1000, 1, date(2026, 1, 1), 0, 5)
		self.assertEqual([(line.seq, line.amount) for line in lines], [(1, D("4000.00"))])

	def test_percent_down_payment(self):
		self.assertEqual(down_payment_amount(30000, "Percent", 30), D("9000.00"))

	def test_no_down_payment(self):
		self.assertEqual(down_payment_amount(30000, "None", 999), D("0.00"))


class TestInvalidParameters(unittest.TestCase):
	def test_rejects(self):
		cases = [
			lambda: generate_installments(0, 0, 14, date(2026, 1, 1), 0, 5),
			lambda: generate_installments(1000, 1000, 14, date(2026, 1, 1), 0, 5),
			lambda: generate_installments(1000, 2000, 14, date(2026, 1, 1), 0, 5),
			lambda: generate_installments(1000, 0, 0, date(2026, 1, 1), 0, 5),
			lambda: generate_installments(1000, 0, 61, date(2026, 1, 1), 0, 5),
			lambda: generate_installments(1000, 0, 14, date(2026, 1, 1), 13, 5),
			lambda: generate_installments(1000, 0, 14, date(2026, 1, 1), 0, 29),
			lambda: generate_installments(1000, 0, 14, date(2026, 1, 1), 0, 0),
			lambda: generate_installments(1000, 0, 14, "2026-01-01", 0, 5),
			lambda: generate_installments(10, 0, 30, date(2026, 1, 1), 0, 5),
			lambda: down_payment_amount(1000, "Fixed", 0),
			lambda: down_payment_amount(1000, "Percent", 101),
			lambda: down_payment_amount(1000, "Fixed", 1001),
			lambda: down_payment_amount(1000, "Half", 10),
		]
		for i, case in enumerate(cases):
			with self.subTest(case=i), self.assertRaises(ScheduleError):
				case()


if __name__ == "__main__":
	unittest.main()
