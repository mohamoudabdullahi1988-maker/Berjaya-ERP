"""Pure boundaries for reporting only; no posting or allocation implementation."""

import unittest
from datetime import date
from decimal import Decimal

from sidra_realestate.services.executive_metrics import (
	decimal_amount,
	money,
	month_starts,
	period_window,
	stage_date_exception,
)


class TestExecutiveMetrics(unittest.TestCase):
	def test_inclusive_period_windows(self):
		today = date(2026, 11, 8)
		self.assertEqual(period_window("this_month", today), (date(2026, 11, 1), today))
		for period, days in (("last_30_days", 30), ("last_90_days", 90)):
			start, end = period_window(period, today)
			self.assertEqual((end - start).days + 1, days)
		with self.assertRaises(ValueError):
			period_window("forever", today)

	def test_exact_amounts_and_unknown_values(self):
		self.assertEqual(money(decimal_amount("0.10") + decimal_amount("0.20")), "0.30")
		self.assertEqual(money("0"), "0.00")
		self.assertEqual(money(Decimal("12.345")), "12.35")
		for value in (None, "", " ", True, "NaN", "Infinity", float("inf")):
			with self.assertRaises(ValueError):
				decimal_amount(value)

	def test_months_cross_year_and_leap_day(self):
		self.assertEqual(
			month_starts(date(2024, 2, 29)),
			[
				date(2023, 9, 1),
				date(2023, 10, 1),
				date(2023, 11, 1),
				date(2023, 12, 1),
				date(2024, 1, 1),
				date(2024, 2, 1),
			],
		)

	def test_recorded_stage_dates_are_not_a_baseline(self):
		today = date(2026, 11, 8)
		self.assertFalse(stage_date_exception({"completion_pct": 0}, today))
		self.assertFalse(stage_date_exception({"planned_end": "2026-11-08", "completion_pct": 0}, today))
		self.assertTrue(stage_date_exception({"planned_end": "2026-11-07", "completion_pct": None}, today))
		self.assertFalse(stage_date_exception({"planned_end": "2026-11-07", "completion_pct": 100}, today))
		self.assertTrue(
			stage_date_exception({"planned_end": "2026-11-06", "actual_end": "2026-11-07"}, today)
		)
		self.assertFalse(
			stage_date_exception({"planned_end": "2026-11-07", "actual_end": "2026-11-07"}, today)
		)
