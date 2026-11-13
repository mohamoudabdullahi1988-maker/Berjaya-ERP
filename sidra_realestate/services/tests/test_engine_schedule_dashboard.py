"""Calendar boundaries and exact gross obligations, independent of payment assumptions."""

import unittest
from datetime import date

from sidra_realestate.services.schedule_dashboard import calendar_snapshot, month_bounds


class TestScheduleDashboard(unittest.TestCase):
	def row(self, day, amount, name="ROW"):
		return {"id": name, "contract_id": "CONTRACT", "due_date": day, "amount": amount}

	def test_leap_year_december_and_invalid_months(self):
		self.assertEqual(month_bounds("2024-02")[1], date(2024, 2, 29))
		self.assertEqual(month_bounds("2026-12")[1], date(2026, 12, 31))
		for value in (None, "2026-1", "2026-00", "2026-13", "2026-11-01", "1899-01"):
			with self.subTest(value=value), self.assertRaises(ValueError):
				month_bounds(value)

	def test_dates_are_inclusive_and_amounts_are_exact(self):
		rows = [
			self.row("2026-10-31", "999"),
			self.row("2026-11-01", "0.10", "A"),
			self.row("2026-11-13", "0.20", "B"),
			self.row("2026-11-30", "1.01", "C"),
			self.row("2026-12-01", "999"),
		]
		data = calendar_snapshot(rows, "2026-11", date(2026, 11, 13))
		self.assertEqual(data["summary"]["month"], {"amount": "1.31", "count": 3})
		self.assertEqual([row["date_state"] for row in data["events"]], ["past_due", "today", "upcoming"])
		self.assertEqual(data["summary"]["today"]["amount"], "0.20")
		self.assertFalse(data["allocation_available"])
		self.assertEqual(data["basis"], "gross_schedule")

	def test_missing_or_nonfinite_amount_is_unknown_not_zero(self):
		for value in (None, "", "NaN", "Infinity", "-1", True):
			with self.subTest(value=value):
				data = calendar_snapshot([self.row("2026-11-13", value)], "2026-11", date(2026, 11, 13))
				self.assertIsNone(data["summary"]["today"]["amount"])
				self.assertIsNone(data["days"][0]["amount"])
				self.assertEqual(data["summary"]["today"]["count"], 1)

	def test_empty_month_is_a_known_zero(self):
		data = calendar_snapshot([], "2026-11", date(2026, 11, 13))
		self.assertEqual(data["summary"]["month"], {"amount": "0.00", "count": 0})
		self.assertEqual(data["events"], [])
