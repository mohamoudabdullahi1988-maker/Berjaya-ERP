"""Pure tests for the title deadline rules (SAL-18; decision G12). No Frappe needed."""

import unittest
from datetime import date

from sidra_realestate.services.title import (
	AWAITING,
	DUE_SOON,
	HANDED_OVER,
	HANDED_OVER_LATE,
	IN_PROGRESS,
	NO_DEADLINE,
	OVERDUE,
	deadline_date,
	title_state,
)

PAID = date(2026, 11, 1)
DEADLINE = date(2026, 11, 21)


class TestDeadline(unittest.TestCase):
	def test_twenty_days_from_final_payment(self):
		self.assertEqual(deadline_date(PAID, 20), DEADLINE)
		self.assertEqual(deadline_date(date(2026, 12, 20), 20), date(2027, 1, 9))

	def test_no_deadline_without_date_or_days(self):
		self.assertIsNone(deadline_date(None, 20))
		self.assertIsNone(deadline_date(PAID, 0))
		self.assertIsNone(deadline_date(PAID, None))


class TestState(unittest.TestCase):
	def state(self, today, **values):
		values = {"final_payment_confirmed": True, "deadline": DEADLINE, **values}
		return title_state(today, **values)

	def test_before_confirmation(self):
		self.assertEqual(self.state(PAID, final_payment_confirmed=False), (AWAITING, 0))

	def test_contract_without_deadline(self):
		self.assertEqual(self.state(PAID, deadline=None), (NO_DEADLINE, 0))

	def test_alert_five_days_before(self):
		self.assertEqual(self.state(date(2026, 11, 15)), (IN_PROGRESS, 0))  # 6 days left
		self.assertEqual(self.state(date(2026, 11, 16)), (DUE_SOON, 0))  # 5 days left
		self.assertEqual(self.state(DEADLINE), (DUE_SOON, 0))  # the deadline day itself is not late

	def test_overdue_counts_days(self):
		self.assertEqual(self.state(date(2026, 11, 22)), (OVERDUE, 1))
		self.assertEqual(self.state(date(2026, 12, 21)), (OVERDUE, 30))

	def test_handover(self):
		self.assertEqual(self.state(date(2026, 12, 30), handed_over_on=DEADLINE), (HANDED_OVER, 0))
		self.assertEqual(
			self.state(date(2026, 12, 30), handed_over_on=date(2026, 11, 24)), (HANDED_OVER_LATE, 3)
		)
		self.assertEqual(self.state(PAID, deadline=None, handed_over_on=PAID), (HANDED_OVER, 0))


if __name__ == "__main__":
	unittest.main()
