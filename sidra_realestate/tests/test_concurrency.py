# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Concurrency regressions for review findings 2 (lock order) and 3 (notary reference).

Each scenario commits its records so a second database connection can see them, runs one
action on the primary connection without committing (it holds its locks), and the
competing action on the secondary connection with a 1-second lock wait. The secondary
must wait for the lock and time out rather than deadlock or slip through, and once the
primary commits, it must see the committed state and refuse. Everything committed is
deleted afterwards.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.services import units as unit_service
from sidra_realestate.services.reservations import cancel_reservation, expire_reservations, reserve_unit
from sidra_realestate.services.units import UnitNotAvailable
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	OTHER_BUYER,
	attach_signed_copy,
	ensure_base_records,
	make_scheme,
	make_unit,
	signing_values,
	unique,
)

CHILD_TABLES = (
	"Sidra Contract Unit",
	"Sidra Contract Party",
	"Sidra Contract Clause Line",
	"Sidra Installment Line",
)


class TestConcurrency(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		cls.scheme = make_scheme("_TEST-CONC")
		frappe.db.commit()

	# ------------------------------------------------------------ fixtures
	def setUp(self):
		super().setUp()
		# Frappe v16.55.2 IntegrationTestCase.secondary_connection() saves the "current"
		# connection only after opening the new one on first use, so it leaves the secondary
		# as frappe.local.db and later code silently runs on it. Open it here, put the real
		# primary back, and close it when the test ends.
		frappe.local.db = self._primary_connection
		with self.secondary_connection():
			pass
		frappe.local.db = self._primary_connection
		self.addCleanup(self._secondary_connection.close)
		self.addCleanup(setattr, frappe.local, "db", self._primary_connection)
		self.units, self.contracts = [], []
		self.addCleanup(self._purge)

	def unit(self):
		name = make_unit(unique("_T-CONC"), self.scheme).name
		self.units.append(name)
		return name

	def contract(self, units, customer=BUYER, **values):
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"customer": customer,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"contract_profile": "Profile A",
				"agreed_price": 1000 * len(units),
				"units": [{"unit": u, "allocated_price": 1000} for u in units],
				**signing_values(),
				**values,
			}
		).insert(ignore_permissions=True)
		self.contracts.append(doc.name)
		return attach_signed_copy(doc).name

	def submit(self, name):
		frappe.get_doc("Sidra Sale Contract", name).submit()

	def in_secondary(self, action, *, expect):
		"""Run `action` on the second connection with a 1 s lock wait; it must raise `expect`."""
		with self.secondary_connection():
			frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 1")
			try:
				with self.assertRaises(expect):
					action()
			finally:
				frappe.db.rollback()

	def commit_primary(self):
		with self.primary_connection():
			frappe.db.commit()

	def _purge(self):
		with self.primary_connection():
			frappe.db.rollback()
			for name in self.contracts:
				for child in CHILD_TABLES:
					frappe.db.delete(child, {"parent": name})
				frappe.db.delete("File", {"attached_to_name": name})
				frappe.db.delete("Sidra Sale Contract", {"name": name})
			for unit in self.units:
				frappe.db.delete("Sidra Reservation", {"unit": unit})
				frappe.db.delete("Sidra Unit Price History", {"unit": unit})
				frappe.db.delete("Sidra Unit", {"name": unit})
			frappe.db.commit()

	# ------------------------------------------------------------ finding 2: lock order
	def test_units_are_locked_in_name_order(self):
		names = sorted(self.unit() for _ in range(3))
		contract = self.contract([names[2], names[0], names[1]])
		calls = []
		real = unit_service.lock_unit

		def spy(name):
			calls.append(name)
			return real(name)

		with patch.object(unit_service, "lock_unit", side_effect=spy):
			self.submit(contract)
		self.assertEqual(calls, names)

	def record_locks(self):
		"""Record every row lock taken through lock_unit or get_doc(..., for_update=True)."""
		calls = []
		real_lock_unit = unit_service.lock_unit
		real_get_doc = frappe.get_doc

		def lock_unit(name):
			calls.append(("Sidra Unit", name))
			return real_lock_unit(name)

		def get_doc(*args, **kwargs):
			if kwargs.get("for_update") and args and args[0] != "Sidra Unit":
				calls.append((args[0], args[1]))
			return real_get_doc(*args, **kwargs)

		patches = [
			patch.object(unit_service, "lock_unit", side_effect=lock_unit),
			patch("sidra_realestate.services.reservations.lock_unit", side_effect=lock_unit),
			patch("frappe.get_doc", side_effect=get_doc),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		return calls

	def assert_units_before_reservations(self, calls):
		kinds = [doctype for doctype, _ in calls]
		self.assertIn("Sidra Unit", kinds)
		self.assertIn("Sidra Reservation", kinds)
		self.assertLess(
			max(i for i, k in enumerate(kinds) if k == "Sidra Unit"),
			min(i for i, k in enumerate(kinds) if k == "Sidra Reservation"),
			calls,
		)

	def test_cancel_expiry_and_submit_all_lock_unit_before_reservation(self):
		for action in ("cancel", "expire", "submit"):
			with self.subTest(action=action):
				unit = self.unit()
				reservation = reserve_unit(unit, BUYER)["reservation"]
				contract = self.contract([unit]) if action == "submit" else None
				if action == "expire":
					start = add_days(today(), -8)
					frappe.db.set_value(
						"Sidra Reservation",
						reservation,
						{"reserved_on": start, "expires_on": add_days(start, 7)},
					)
				calls = self.record_locks()
				if action == "cancel":
					cancel_reservation(reservation)
				elif action == "expire":
					expire_reservations()
				else:
					self.submit(contract)
				patch.stopall()
				self.assert_units_before_reservations(calls)

	def test_cancel_waits_for_submit_and_then_refuses(self):
		unit = self.unit()
		reservation = reserve_unit(unit, BUYER)["reservation"]
		contract = self.contract([unit])
		frappe.db.commit()

		with self.primary_connection():
			self.submit(contract)  # holds the unit, then the reservation
		self.in_secondary(lambda: cancel_reservation(reservation), expect=frappe.QueryTimeoutError)
		self.commit_primary()
		self.in_secondary(lambda: cancel_reservation(reservation), expect=frappe.ValidationError)

		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")
		self.assertEqual(frappe.db.get_value("Sidra Reservation", reservation, "status"), "Converted")

	def test_expiry_waits_for_submit_and_then_skips(self):
		unit = self.unit()
		reservation = reserve_unit(unit, BUYER)["reservation"]
		start = add_days(today(), -8)
		frappe.db.set_value(
			"Sidra Reservation", reservation, {"reserved_on": start, "expires_on": add_days(start, 7)}
		)
		contract = self.contract([unit])
		frappe.db.commit()

		with self.primary_connection():
			self.submit(contract)
		self.in_secondary(expire_reservations, expect=frappe.QueryTimeoutError)
		self.commit_primary()
		with self.secondary_connection():
			expire_reservations()  # finds nothing active any more
			frappe.db.commit()

		self.assertEqual(frappe.db.get_value("Sidra Reservation", reservation, "status"), "Converted")
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")

	def test_submit_waits_for_cancel_and_then_sees_released_unit(self):
		unit = self.unit()
		reservation = reserve_unit(unit, BUYER)["reservation"]
		contract = self.contract([unit])
		frappe.db.commit()

		with self.primary_connection():
			cancel_reservation(reservation)  # holds the unit, then the reservation
		self.in_secondary(lambda: self.submit(contract), expect=frappe.QueryTimeoutError)
		self.commit_primary()
		with self.secondary_connection():
			self.submit(contract)  # the unit is Available again, so the buyer's contract proceeds
			frappe.db.commit()

		self.assertEqual(frappe.db.get_value("Sidra Reservation", reservation, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Under Contract")

	def test_multi_unit_contracts_in_opposite_order_wait_not_deadlock(self):
		a, b = sorted([self.unit(), self.unit()])
		first = self.contract([b, a])
		second = self.contract([a, b], customer=OTHER_BUYER)
		frappe.db.commit()

		with self.primary_connection():
			self.submit(first)
		self.in_secondary(lambda: self.submit(second), expect=frappe.QueryTimeoutError)
		self.commit_primary()
		self.in_secondary(lambda: self.submit(second), expect=UnitNotAvailable)

		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", second, "docstatus"), 0)
		for unit in (a, b):
			self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "current_contract"), first)

	# ------------------------------------------------------------ finding 3: notary reference
	def test_concurrent_submits_with_one_notary_reference(self):
		reference = "IPN/HL/" + str(int(frappe.generate_hash(length=6), 16) % 1000).zfill(3) + "/2098"
		first = self.contract([self.unit()], notary_reference=reference)
		second = self.contract([self.unit()], notary_reference=reference, customer=OTHER_BUYER)
		frappe.db.commit()

		with self.primary_connection():
			self.submit(first)  # writes the unique key, not yet committed
		# the second submit cannot see the first, passes the lookup, then waits on the unique index
		self.in_secondary(lambda: self.submit(second), expect=frappe.QueryTimeoutError)
		self.commit_primary()
		self.in_secondary(lambda: self.submit(second), expect=frappe.ValidationError)

		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", second, "docstatus"), 0)
		self.assertEqual(
			frappe.get_all("Sidra Sale Contract", filters={"notary_reference_key": reference}, pluck="name"),
			[first],
		)

	# ------------------------------------------------------------ contract capture: external reference
	def test_concurrent_confirmations_with_one_external_reference(self):
		reference = "EXT-CONC-" + frappe.generate_hash(length=6).upper()
		external = {
			"source": "External (registered)",
			"external_reference": reference,
			"schedule": [{"row_type": "Installment", "due_date": "2026-12-10", "amount": 1000}],
		}
		first = self.contract([self.unit()], **external)
		second = self.contract([self.unit()], customer=OTHER_BUYER, **external)
		frappe.db.commit()

		with self.primary_connection():
			self.submit(first)  # writes the unique key, not yet committed
		self.in_secondary(lambda: self.submit(second), expect=frappe.QueryTimeoutError)
		self.commit_primary()
		self.in_secondary(lambda: self.submit(second), expect=frappe.ValidationError)

		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", second, "docstatus"), 0)
		self.assertEqual(
			frappe.get_all(
				"Sidra Sale Contract",
				filters={"external_reference_key": f"{COMPANY}::{reference}"},
				pluck="name",
			),
			[first],
		)
