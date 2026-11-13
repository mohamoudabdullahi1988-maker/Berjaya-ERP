"""Pure tests for the pilot demonstration dataset plan (decision G15). No Frappe needed."""

import re
import unittest
from datetime import date
from decimal import Decimal

from sidra_realestate.services.pilot_dataset import (
	MONTHS,
	PREFIX,
	Plan,
	add_months,
	build,
	money,
	totals,
)

AS_OF = date(2026, 11, 13)
D = Decimal


class TestAddMonths(unittest.TestCase):
	def test_forward_and_back(self):
		self.assertEqual(add_months(date(2026, 1, 15), 1), date(2026, 2, 15))
		self.assertEqual(add_months(date(2026, 1, 15), -1), date(2025, 12, 15))
		self.assertEqual(add_months(date(2026, 11, 13), -MONTHS), date(2025, 11, 13))

	def test_clamps_to_short_month(self):
		self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
		self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))

	def test_year_boundary(self):
		self.assertEqual(add_months(date(2026, 12, 1), 1), date(2027, 1, 1))
		self.assertEqual(add_months(date(2026, 1, 1), -1), date(2025, 12, 1))


class TestDeterminism(unittest.TestCase):
	def test_two_builds_are_identical(self):
		first, second = build(AS_OF), build(AS_OF)
		self.assertEqual(first.counts(), second.counts())
		self.assertEqual(first.units, second.units)
		self.assertEqual(first.contracts, second.contracts)
		self.assertEqual(totals(first), totals(second))

	def test_spans_twelve_months(self):
		plan = build(AS_OF)
		self.assertEqual(plan.from_date, date(2025, 11, 13))
		self.assertEqual(plan.as_of, AS_OF)


class TestCoverage(unittest.TestCase):
	"""Every module the client is shown must have records, or the demo has a blank screen."""

	def setUp(self):
		self.plan = build(AS_OF)

	def test_every_collection_is_populated(self):
		for name, count in self.plan.counts().items():
			with self.subTest(collection=name):
				self.assertGreater(count, 0, f"{name} would be empty in the demo")

	def test_volumes(self):
		counts = self.plan.counts()
		self.assertEqual(counts["schemes"], 4)
		self.assertEqual(counts["units"], 120)
		self.assertEqual(counts["customers"], 40)
		self.assertEqual(counts["contracts"], 45)
		self.assertEqual(counts["jobs"], 25)
		self.assertEqual(counts["invoices"], 95)

	def test_names_are_prefixed_and_fictional(self):
		for unit in self.plan.units:
			self.assertTrue(unit["unit_code"].startswith(PREFIX + "-"))
		for scheme in self.plan.schemes:
			self.assertTrue(scheme["scheme_code"].startswith(PREFIX + "-"))

	def test_unit_codes_are_unique(self):
		codes = [u["unit_code"] for u in self.plan.units]
		self.assertEqual(len(codes), len(set(codes)))

	def test_customer_names_are_unique(self):
		names = [c["name"] for c in self.plan.customers]
		self.assertEqual(len(names), len(set(names)))

	def test_no_unit_is_sold_twice(self):
		taken = [u["unit"] for c in self.plan.contracts for u in c["units"]]
		taken += [r["unit"] for r in self.plan.reservations]
		self.assertEqual(len(taken), len(set(taken)), "a unit is both reserved and contracted")

	def test_mixed_statuses_so_reports_are_not_flat(self):
		self.assertGreater(len({q["status"] for q in self.plan.quotations}), 1)
		self.assertGreater(len({r["status"] for r in self.plan.reservations}), 1)
		self.assertGreater(len({c["contract_type"] for c in self.plan.contracts}), 1)
		self.assertGreater(len({c["source"] for c in self.plan.contracts}), 1)
		self.assertGreater(len({j["status"] for j in self.plan.jobs}), 1)
		self.assertGreater(len({j["service_type"] for j in self.plan.jobs}), 1)

	def test_some_contracts_stay_draft(self):
		self.assertTrue(any(not c["submit"] for c in self.plan.contracts))
		self.assertTrue(any(c["submit"] for c in self.plan.contracts))

	def test_some_customers_are_unverified_for_the_kyc_gate(self):
		self.assertTrue(any(not c["verified"] for c in self.plan.customers))
		self.assertTrue(any(c["verified"] for c in self.plan.customers))

	def test_contracts_only_use_verified_buyers(self):
		verified = {c["name"] for c in self.plan.customers if c["verified"]}
		for contract in self.plan.contracts:
			self.assertIn(contract["customer"], verified)

	def test_notary_references_match_the_registry_format(self):
		"""SAL-19: the contract refuses anything that is not IPN/HL/NNN/YYYY."""
		pattern = re.compile(r"^IPN/HL/\d{3}/\d{4}$")
		# References the rest of the suite fixes; a notary reference is unique site-wide.
		taken = {"042", "077", "078", "079", "081", "901", "902", "903"}
		seen = set()
		for contract in self.plan.contracts:
			reference = contract["notary_reference"]
			self.assertRegex(reference, pattern, contract["reference"])
			self.assertNotIn(reference, seen, "notary references must be unique")
			self.assertNotIn(reference.split("/")[2], taken, "collides with another test's reference")
			seen.add(reference)

	def test_title_dates_are_never_in_the_future(self):
		"""The tracker refuses a future final payment, or a handover before that payment."""
		signed = {c["reference"]: c["signed_on"] for c in self.plan.contracts}
		for title in self.plan.titles:
			self.assertLessEqual(title["final_payment_date"], AS_OF, title["reference"])
			self.assertGreaterEqual(title["final_payment_date"], signed[title["contract"]])
			if title["handed_over_on"]:
				self.assertLessEqual(title["handed_over_on"], AS_OF)
				self.assertGreaterEqual(title["handed_over_on"], title["final_payment_date"])

	def test_reservations_carry_a_hold_length_not_dates(self):
		"""The Reserve Unit service dates them; a plan date here would be silently ignored."""
		for entry in self.plan.reservations:
			self.assertNotIn("reserved_on", entry)
			self.assertGreaterEqual(entry["days"], 1)
			self.assertIn(entry["status"], {"Active", "Expired", "Cancelled"})

	def test_price_reviews_are_scheduled_ahead(self):
		"""A unit records a price the day it is created, and a new one must take effect after it."""
		for entry in self.plan.price_history:
			self.assertGreater(entry["effective_from"], AS_OF, entry["unit"])

	def test_everything_is_dated_inside_the_window(self):
		for contract in self.plan.contracts:
			self.assertLessEqual(contract["signed_on"], AS_OF)
			self.assertGreaterEqual(contract["signed_on"], self.plan.from_date)
		for invoice in self.plan.invoices:
			self.assertLessEqual(invoice["posting_date"], AS_OF)
			self.assertGreaterEqual(invoice["posting_date"], self.plan.from_date)


class TestSchedules(unittest.TestCase):
	def setUp(self):
		self.plan = build(AS_OF)

	def test_installment_contracts_have_a_schedule(self):
		for contract in self.plan.contracts:
			if contract["contract_type"] == "Installment":
				self.assertEqual(len(contract["schedule"]), contract["installments"])
			else:
				self.assertEqual(contract["schedule"], [])

	def test_schedule_adds_up_to_the_balance_exactly(self):
		"""Rounding must land on the last row, never leave a difference (handover §9 tolerance)."""
		for contract in self.plan.contracts:
			if contract["contract_type"] != "Installment":
				continue
			total = money(sum(row["amount"] for row in contract["schedule"]))
			expected = money(contract["agreed_price"] - contract["down_payment"])
			self.assertEqual(total, expected, contract["reference"])

	def test_schedule_dates_ascend(self):
		for contract in self.plan.contracts:
			dates = [row["due_date"] for row in contract["schedule"]]
			self.assertEqual(dates, sorted(dates))

	def test_down_payment_is_zero_on_cash_contracts(self):
		for contract in self.plan.contracts:
			if contract["contract_type"] == "Cash":
				self.assertEqual(contract["down_payment"], D("0.00"))


class TestFinanceTotals(unittest.TestCase):
	def setUp(self):
		self.plan = build(AS_OF)
		self.figures = totals(self.plan)

	def test_balance_sheet_identity(self):
		"""Assets = liabilities + capital + profit, or the demo's Balance Sheet will not balance."""
		assets = self.figures["bank"] + self.figures["receivables"]
		profit = self.figures["revenue"] - self.figures["expenses"]
		self.assertEqual(assets, self.figures["payables"] + self.figures["capital"] + profit)

	def test_receivables_and_payables_are_positive(self):
		"""Something must be outstanding, or AR and AP ageing reports open empty."""
		self.assertGreater(self.figures["receivables"], 0)
		self.assertGreater(self.figures["payables"], 0)

	def test_receipts_never_exceed_revenue(self):
		self.assertLessEqual(self.figures["receipts"], self.figures["revenue"])
		self.assertLessEqual(self.figures["supplier_payments"], self.figures["expenses"])

	def test_every_amount_is_two_decimals(self):
		for key, value in self.figures.items():
			with self.subTest(figure=key):
				self.assertEqual(value, money(value))

	def test_invoice_ageing_has_paid_part_paid_and_open(self):
		sales = [i for i in self.plan.invoices if i["kind"] == "Sales Invoice"]
		self.assertTrue(any(i["paid"] == i["amount"] for i in sales))
		self.assertTrue(any(D(0) < i["paid"] < i["amount"] for i in sales))
		self.assertTrue(any(i["paid"] == D(0) for i in sales))


class TestPlanShape(unittest.TestCase):
	def test_counts_covers_every_collection(self):
		plan = build(AS_OF)
		fields = {f for f in Plan.__dataclass_fields__ if f not in ("as_of", "from_date")}
		self.assertEqual(set(plan.counts()), fields)


if __name__ == "__main__":
	unittest.main()
