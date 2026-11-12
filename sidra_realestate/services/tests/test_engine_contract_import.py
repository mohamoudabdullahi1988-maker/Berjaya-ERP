"""Spreadsheet reader for the contract import (decision G5). Pure tests: no Frappe."""

import unittest
from datetime import date, datetime
from decimal import Decimal

from sidra_realestate.services.contract_import import parse_money, parse_rows

HEADER = [
	"External Reference",
	"Customer",
	"Signed On",
	"Agreed Price",
	"Unit",
	"Unit Price",
	"Row Type",
	"Due Date",
	"Amount",
]


class TestContractImportReader(unittest.TestCase):
	def test_nonfinite_and_out_of_range_amounts_are_validation_errors(self):
		for value in ("NaN", "sNaN", "Infinity", "-Infinity", "1e999999", "1e-999999"):
			with self.subTest(value=value), self.assertRaises(ValueError):
				parse_money(value)
		for column in ("Agreed Price", "Unit Price", "Amount"):
			row = ["EXT-INVALID", "Buyer A", "2026-01-15", "100", "U-1", "100", "", "2026-02-10", "100"]
			row[HEADER.index(column)] = "NaN"
			_, errors = parse_rows([HEADER, row])
			self.assertTrue(any(error.startswith("Row 2:") for error in errors))

	def test_groups_rows_into_contracts(self):
		contracts, errors = parse_rows(
			[
				HEADER,
				["ext-1 ", "Buyer A", "15/01/2026", "10,000", "U-1", "5000", "", "2026-02-10", "5000"],
				["EXT-1", "", "", "", "U-2", "5000", "Fee", "10/03/2026", "5000.00"],
				[
					"EXT-2",
					"Buyer B",
					datetime(2025, 3, 1),
					9000,
					"U-3",
					None,
					"Down payment",
					date(2025, 3, 1),
					9000,
				],
				["", "", "", "", "", "", "", "", ""],
			]
		)
		self.assertEqual(errors, [])
		self.assertEqual([c.external_reference for c in contracts], ["EXT-1", "EXT-2"])
		first, second = contracts
		self.assertEqual(
			(first.customer, first.signed_on, first.agreed_price),
			("Buyer A", date(2026, 1, 15), Decimal("10000.00")),
		)
		self.assertEqual(first.units, [("U-1", Decimal("5000.00")), ("U-2", Decimal("5000.00"))])
		self.assertEqual(
			[(t, d, a) for t, d, a, _ in first.schedule],
			[
				("Installment", date(2026, 2, 10), Decimal("5000.00")),
				("Fee", date(2026, 3, 10), Decimal("5000.00")),
			],
		)
		self.assertEqual(second.units, [("U-3", Decimal("9000.00"))])  # single unit takes the price
		self.assertEqual(second.schedule[0][0], "Down payment")

	def test_missing_columns(self):
		_, errors = parse_rows([["External Reference", "Customer"]])
		self.assertIn("Missing column(s)", errors[0])

	def test_row_errors_name_the_row(self):
		_, errors = parse_rows(
			[
				HEADER,
				["EXT-1", "Buyer A", "2026-13-40", "100", "U-1", "", "", "2026-02-10", "100"],
				["EXT-2", "Buyer B", "2026-01-15", "100", "U-2", "", "Gift", "2026-02-10", "100"],
				["EXT-3", "Buyer C", "2026-01-15", "100", "U-3", "", "", "2026-02-10", "-5"],
				["EXT-4", "Buyer D", "2026-01-15", "100", "U-4", "", "", "2026-02-10", "10.005"],
			]
		)
		self.assertEqual([e.split(":")[0] for e in errors[:4]], ["Row 2", "Row 3", "Row 4", "Row 5"])

	def test_conflicting_contract_values(self):
		_, errors = parse_rows(
			[
				HEADER,
				["EXT-1", "Buyer A", "2026-01-15", "100", "U-1", "", "", "2026-02-10", "50"],
				["EXT-1", "Buyer B", "", "", "U-1", "", "", "2026-03-10", "50"],
			]
		)
		self.assertTrue(any("customer" in e and "differs" in e for e in errors))

	def test_unit_prices_must_add_up(self):
		_, errors = parse_rows(
			[
				HEADER,
				["EXT-1", "Buyer A", "2026-01-15", "100", "U-1", "40", "", "2026-02-10", "100"],
				["EXT-1", "", "", "", "U-2", "", "", "2026-03-10", "0.01"],
			]
		)
		self.assertTrue(any("unit_price for every unit" in e for e in errors))


if __name__ == "__main__":
	unittest.main()
