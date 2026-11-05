# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Reservation service (SAL-04; SRS v2.0 §3.2, §6; handoff v2.0 first-PR checklist)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.services.reservations import cancel_reservation, expire_reservations, reserve_unit
from sidra_realestate.services.units import UnitNotAvailable
from sidra_realestate.tests.helpers import (
	BUYER,
	OTHER_BUYER,
	OUTSIDER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_scheme,
	make_unit,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Customer", "Company", "Sidra Sale Contract"]


class TestReservationService(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		cls.scheme = make_scheme("_TEST-RES")
		frappe.db.commit()

	def new_unit(self):
		return make_unit(unique("_T-RES"), self.scheme)

	def test_reserve_marks_unit_reserved(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER)

		unit.reload()
		reservation = frappe.get_doc("Sidra Reservation", result["reservation"])
		self.assertEqual(unit.status, "Reserved")
		self.assertEqual(unit.current_reservation, reservation.name)
		self.assertEqual(reservation.status, "Active")
		self.assertEqual(reservation.customer, BUYER)
		self.assertEqual(getdate(reservation.expires_on), getdate(add_days(today(), 7)))

	def test_custom_days(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER, days=3)
		self.assertEqual(getdate(result["expires_on"]), getdate(add_days(today(), 3)))
		with self.assertRaises(frappe.ValidationError):
			reserve_unit(self.new_unit().name, BUYER, days=0)

	def test_second_reservation_is_rejected(self):
		unit = self.new_unit()
		reserve_unit(unit.name, BUYER)
		with self.assertRaises(UnitNotAvailable):
			reserve_unit(unit.name, OTHER_BUYER)

	def test_unknown_unit_or_customer(self):
		with self.assertRaises(frappe.DoesNotExistError):
			reserve_unit("_NO-SUCH-UNIT", BUYER)
		with self.assertRaises(frappe.DoesNotExistError):
			reserve_unit(self.new_unit().name, "_No Such Customer")

	def test_sales_user_can_reserve(self):
		unit = self.new_unit()
		with as_user(SALES_USER):
			result = reserve_unit(unit.name, BUYER)
		self.assertTrue(frappe.db.exists("Sidra Reservation", result["reservation"]))

	def test_unrelated_user_is_rejected(self):
		unit = self.new_unit()
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			reserve_unit(unit.name, BUYER)
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Available")

	def test_reservation_cannot_be_created_directly(self):
		unit = self.new_unit()
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Reservation",
				"unit": unit.name,
				"customer": BUYER,
				"reserved_on": today(),
				"expires_on": add_days(today(), 7),
			}
		)
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)

	def test_cancel_releases_unit(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER)
		cancel_reservation(result["reservation"])
		self.assertEqual(frappe.db.get_value("Sidra Reservation", result["reservation"], "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Available")
		with self.assertRaises(frappe.ValidationError):
			cancel_reservation(result["reservation"])

	def test_daily_expiry_releases_unit(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER)
		self._backdate(result["reservation"], days_ago=8, length=7)

		expire_reservations()

		self.assertEqual(frappe.db.get_value("Sidra Reservation", result["reservation"], "status"), "Expired")
		unit.reload()
		self.assertEqual(unit.status, "Available")
		self.assertIsNone(unit.current_reservation)

	def test_expiry_keeps_reservation_valid_through_last_day(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER)
		self._backdate(result["reservation"], days_ago=7, length=7)  # expires today
		expire_reservations()
		self.assertEqual(frappe.db.get_value("Sidra Reservation", result["reservation"], "status"), "Active")

	def test_expiry_does_not_release_a_newer_allocation(self):
		unit = self.new_unit()
		result = reserve_unit(unit.name, BUYER)
		self._backdate(result["reservation"], days_ago=8, length=7)
		frappe.db.set_value(
			"Sidra Unit", unit.name, {"status": "Under Contract", "current_reservation": None}
		)  # allocated since

		expire_reservations()

		self.assertEqual(frappe.db.get_value("Sidra Reservation", result["reservation"], "status"), "Expired")
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Under Contract")

	def test_concurrent_reservations_exactly_one_wins(self):
		"""Two sessions reserve the same unit at once: the row lock lets one through."""
		unit = self.new_unit()
		frappe.db.commit()  # the second connection must see the unit
		self.addCleanup(self._delete_committed_unit, unit.name)

		with self.primary_connection():
			first = reserve_unit(unit.name, BUYER)  # holds the unit row lock, not committed

		with self.secondary_connection():
			frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 1")
			with self.assertRaises(frappe.QueryTimeoutError):
				reserve_unit(unit.name, OTHER_BUYER)
			frappe.db.rollback()

		with self.primary_connection():
			frappe.db.commit()

		with self.secondary_connection():
			with self.assertRaises(UnitNotAvailable):
				reserve_unit(unit.name, OTHER_BUYER)
			frappe.db.rollback()

		with self.primary_connection():
			reservations = frappe.get_all("Sidra Reservation", filters={"unit": unit.name}, pluck="name")
			self.assertEqual(reservations, [first["reservation"]])
			self.assertEqual(frappe.db.get_value("Sidra Unit", unit.name, "status"), "Reserved")

	def _backdate(self, reservation, days_ago, length):
		start = add_days(today(), -days_ago)
		frappe.db.set_value(
			"Sidra Reservation", reservation, {"reserved_on": start, "expires_on": add_days(start, length)}
		)

	def _delete_committed_unit(self, unit_name):
		with self.primary_connection():
			frappe.db.rollback()
			frappe.db.delete("Sidra Reservation", {"unit": unit_name})
			frappe.db.delete("Sidra Unit", {"name": unit_name})
			frappe.db.commit()
