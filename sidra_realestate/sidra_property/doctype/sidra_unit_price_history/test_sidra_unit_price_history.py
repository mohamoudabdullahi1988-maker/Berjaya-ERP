# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Price history, per-Company access and bulk import (SAL-01, SAL-02; handoff feature/sal-price-history; issue #6)."""

import csv
import os
import tempfile

import frappe
from frappe.core.doctype.data_import.data_import import import_file
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.patches.v0_2 import create_initial_unit_prices
from sidra_realestate.services.prices import price_on, refresh_current_prices
from sidra_realestate.services.reservations import reserve_unit
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_COMPANY,
	SALES_USER,
	as_user,
	ensure_base_records,
	ensure_user,
	make_scheme,
	make_unit,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Sidra Scheme", "Company"]

DOCTYPE = "Sidra Unit Price History"
COMPANY_MANAGER = "sidra.manager.tsh@example.com"
COMPANY_SALES = "sidra.sales.tsh@example.com"


class TestSidraUnitPriceHistory(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.scheme = make_scheme("_TEST-PRICE")
		cls.other_scheme = make_scheme("_TEST-PRICE-OTHER", OTHER_COMPANY)
		ensure_user(COMPANY_MANAGER, ["Sidra Sales Manager"])
		cls._restrict_to_company(COMPANY_MANAGER)
		frappe.db.commit()

	def unit(self, price=None, scheme=None):
		values = {"cash_price": price} if price is not None else {}
		return make_unit(unique("_T-PRICE"), scheme or self.scheme, **values)

	def price(self, unit, price, effective_from=None, reason="Price review", submit=True):
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"unit": unit,
				"price": price,
				"effective_from": effective_from or today(),
				"reason": reason,
			}
		).insert(ignore_permissions=True)
		if submit:
			doc.submit()
		return doc

	def history(self, unit):
		return frappe.get_all(
			DOCTYPE,
			filters={"unit": unit, "docstatus": 1},
			fields=["price", "previous_price", "reason", "effective_from"],
			order_by="effective_from asc",
		)

	# ------------------------------------------------------------ history
	def test_unit_created_with_price_gets_initial_entry(self):
		unit = self.unit(price=5500)
		self.assertEqual(
			[(h.price, h.previous_price, h.reason) for h in self.history(unit.name)], [(5500, 0, "Initial price")]
		)
		self.assertEqual(unit.cash_price, 5500)

	def test_unit_without_price_has_no_history(self):
		self.assertEqual(self.history(self.unit().name), [])

	def test_price_change_today_updates_unit_and_keeps_history(self):
		unit = self.unit()
		self.price(unit.name, 5000, add_days(today(), -30), reason="Launch")
		entry = self.price(unit.name, 5500)

		self.assertEqual(entry.previous_price, 5000)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "cash_price"), 5500)
		self.assertEqual([h.price for h in self.history(unit.name)], [5000, 5500])
		self.assertEqual(price_on(unit.name, add_days(today(), -1)), 5000)
		self.assertEqual(price_on(unit.name, add_days(today(), -31)), None)

	def test_future_price_takes_effect_on_its_date(self):
		unit = self.unit(price=5500)
		future = self.price(unit.name, 6000, add_days(today(), 10))
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "cash_price"), 5500)
		self.assertEqual(price_on(unit.name, add_days(today(), 10)), 6000)

		frappe.db.set_value(DOCTYPE, future.name, "effective_from", today())  # time passes
		refresh_current_prices()
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "cash_price"), 6000)

	def test_backdating_before_latest_entry_is_rejected(self):
		unit = self.unit()
		self.price(unit.name, 5000, add_days(today(), -10))
		with self.assertRaises(frappe.ValidationError):
			self.price(unit.name, 4800, add_days(today(), -20))
		with self.assertRaises(frappe.ValidationError):
			self.price(unit.name, 4800, add_days(today(), -10))  # same day

	def test_submitted_entry_cannot_be_edited_or_deleted(self):
		entry = self.price(self.unit().name, 5000)
		entry.price = 4000
		with self.assertRaises(frappe.ValidationError):
			entry.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc(DOCTYPE, entry.name, ignore_permissions=True)

	def test_only_future_entries_can_be_cancelled(self):
		unit = self.unit(price=5500)
		in_force = frappe.get_doc(DOCTYPE, {"unit": unit.name, "docstatus": 1})
		with self.assertRaises(frappe.ValidationError):
			in_force.cancel()

		future = self.price(unit.name, 6000, add_days(today(), 10))
		future.cancel()
		self.assertEqual(frappe.db.get_value(DOCTYPE, future.name, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "cash_price"), 5500)
		# cancelled entry is kept and no longer blocks an earlier date
		self.price(unit.name, 5800, add_days(today(), 5))

	def test_price_must_be_positive_with_reason(self):
		unit = self.unit().name
		with self.assertRaises(frappe.ValidationError):
			self.price(unit, 0)
		with self.assertRaises(frappe.ValidationError):
			self.price(unit, 5000, reason="  ")

	def test_unit_price_cannot_be_edited_by_hand(self):
		unit = self.unit(price=5500)
		unit.reload()
		unit.cash_price = 5000
		with self.assertRaises(frappe.ValidationError):
			unit.save(ignore_permissions=True)

	# ------------------------------------------------------------ permissions
	def test_sales_user_cannot_set_prices(self):
		unit = self.unit().name
		with as_user(SALES_USER), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{"doctype": DOCTYPE, "unit": unit, "price": 5000, "effective_from": today(), "reason": "x"}
			).insert()

	def test_per_company_access(self):
		own = self.unit(price=5500)
		other = self.unit(price=7000, scheme=self.other_scheme)

		with as_user(COMPANY_MANAGER):
			units = set(frappe.get_list("Sidra Unit", pluck="name", limit=0))
			schemes = set(frappe.get_list("Sidra Scheme", pluck="name", limit=0))
			prices = set(frappe.get_list(DOCTYPE, pluck="unit", limit=0))
			self.assertIn(own.name, units)
			self.assertNotIn(other.name, units)
			self.assertNotIn(self.other_scheme, schemes)
			self.assertIn(own.name, prices)
			self.assertNotIn(other.name, prices)

			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Sidra Unit", other.name).check_permission("read")
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					{
						"doctype": DOCTYPE,
						"unit": other.name,
						"price": 7500,
						"effective_from": add_days(today(), 1),
						"reason": "x",
					}
				).insert()
			entry = frappe.get_doc(
				{"doctype": DOCTYPE, "unit": own.name, "price": 5600, "effective_from": add_days(today(), 1), "reason": "x"}
			).insert()
			entry.submit()
		self.assertEqual(entry.company, COMPANY)

	def test_per_company_reservations(self):
		other = self.unit(scheme=self.other_scheme)
		# Match the documented Sales Staff profile so this test reaches the Company
		# restriction rather than failing earlier on Customer access.
		ensure_user(COMPANY_SALES, ["Sidra Sales User", "Sales User"])
		self._restrict_to_company(COMPANY_SALES)
		with as_user(COMPANY_SALES):
			with self.assertRaises(frappe.PermissionError):
				reserve_unit(other.name, BUYER)
			self.assertTrue(reserve_unit(self.unit().name, BUYER)["reservation"])
		self.assertEqual(frappe.db.get_value("Sidra Unit", other.name, "status"), "Available")

	@staticmethod
	def _restrict_to_company(user):
		if not frappe.db.exists("User Permission", {"user": user, "allow": "Company"}):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": "Company",
					"for_value": COMPANY,
					"apply_to_all_doctypes": 1,
				}
			).insert(ignore_permissions=True)

	# ------------------------------------------------------------ import and migration
	def test_bulk_import_units_from_file(self):
		codes = [unique("_T-IMP") for _ in range(3)]
		rows = [
			["Unit Code", "Scheme", "Unit Type", "Plot Fraction", "Dimensions", "Cash Price"],
			[codes[0], self.scheme, "Plot", "Full", "18×24 m", 11000],
			[codes[1], self.scheme, "Plot", "Half", "9×24 m", 5500],
			[codes[2], self.scheme, "Plot", "Half", "9×24 m", ""],
		]
		with tempfile.TemporaryDirectory() as folder:
			path = os.path.join(folder, "units.csv")
			with open(path, "w", newline="", encoding="utf-8") as fh:
				csv.writer(fh).writerows(rows)
			import_file("Sidra Unit", path, "Insert", console=True)  # as `bench data-import`
		self.addCleanup(self._delete_imported, codes)

		for code, price in zip(codes, (11000, 5500, 0), strict=True):
			unit = frappe.get_doc("Sidra Unit", code)
			self.assertEqual((unit.status, unit.company, unit.cash_price), ("Available", COMPANY, price))
			self.assertEqual([h.price for h in self.history(code)], [price] if price else [])

	def test_patch_backfills_units_priced_before_history(self):
		unit = self.unit(price=5500)
		frappe.db.delete(DOCTYPE, {"unit": unit.name})  # as if created before this feature
		create_initial_unit_prices.execute()
		create_initial_unit_prices.execute()  # idempotent

		history = self.history(unit.name)
		self.assertEqual([(h.price, h.reason) for h in history], [(5500, "Initial price")])
		self.assertEqual(getdate(history[0].effective_from), getdate(unit.creation))
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "cash_price"), 5500)

	def _delete_imported(self, codes):
		frappe.db.rollback()
		for code in codes:
			for name in frappe.get_all(DOCTYPE, filters={"unit": code}, pluck="name"):
				frappe.db.delete(DOCTYPE, {"name": name})
			frappe.db.delete("Sidra Unit", {"name": code})
		frappe.db.commit()
