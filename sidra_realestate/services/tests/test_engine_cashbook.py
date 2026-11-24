from decimal import Decimal
from unittest import TestCase

from sidra_realestate.services.cashbook import COLUMNS, amount, statement_rows


class TestCashbookStatement(TestCase):
	def test_parse_reference_and_single_direction(self):
		rows = statement_rows(iter([COLUMNS, ["2026-11-23", " 00017 ", "USD", "300.00", ""]]), "USD", 2)
		self.assertEqual(rows[0]["reference_number"], "00017")
		self.assertEqual(rows[0]["deposit"], Decimal("300.00"))
		self.assertEqual(rows[0]["withdrawal"], Decimal(0))

	def test_reject_wrong_currency_and_invalid_amounts(self):
		for currency, deposit, withdrawal in [
			("EUR", 300, 0),
			("USD", 300, 3),
			("USD", -1, 0),
			("USD", "NaN", 0),
		]:
			with (
				self.subTest(currency=currency, deposit=deposit, withdrawal=withdrawal),
				self.assertRaisesRegex(ValueError, "Row 2"),
			):
				statement_rows(
					iter([COLUMNS, ["2026-11-23", "DEMO", currency, deposit, withdrawal]]), "USD", 2
				)
		self.assertEqual(amount("-10", 2), -10)
		with self.assertRaises(ValueError):
			amount("1.001", 2)
