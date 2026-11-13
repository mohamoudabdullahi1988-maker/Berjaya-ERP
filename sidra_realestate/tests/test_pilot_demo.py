"""The pilot dataset on the disposable CI site: real documents, real ledger, never mocked.

This module is named so that it sorts after `test_finance_demo`, which asserts absolute voucher
counts for the same Company. The assertions here are written against the pilot's own manifest
rather than the Company's totals, so the two remain independent in both directions.
"""

import hashlib
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.finance_demo import COMPANY, FLAGS
from sidra_realestate.pilot_demo import (
	ACCOUNT_PREFIX,
	CUSTOMER_PREFIX,
	ITEM,
	MANIFEST,
	PROFILE,
	SUPPLIER,
	VOUCHER_TYPES,
	create_pilot_demo_data,
	verify_pilot_demo,
)
from sidra_realestate.services.pilot_dataset import PREFIX
from sidra_realestate.tests.helpers import as_user, ensure_base_records, ensure_company

OWN_SCHEME = "_TEST-SH-EXISTING"


def company_units():
	"""Count and checksum of the Company's own units: the pilot must not touch them."""
	rows = frappe.get_all(
		"Sidra Unit",
		filters={"company": COMPANY, "scheme": ("not like", PREFIX + "-%")},
		fields=["*"],
		order_by="name asc",
		limit_page_length=0,
	)
	return len(rows), hashlib.sha256(frappe.as_json(rows).encode()).hexdigest()


def pilot_masters():
	"""Every reserved pilot identity, so a rollback can be proved complete."""
	return (
		frappe.db.count("Account", {"company": COMPANY, "account_name": ("like", ACCOUNT_PREFIX + "%")}),
		frappe.db.count("Customer", {"customer_name": ("like", CUSTOMER_PREFIX + "%")}),
		frappe.db.count("Sidra Scheme", {"scheme_code": ("like", PREFIX + "-%")}),
		frappe.db.count("Sidra Unit", {"scheme": ("like", PREFIX + "-%")}),
		frappe.db.count("Supplier", {"supplier_name": SUPPLIER}),
		frappe.db.count("Item", {"item_code": ITEM}),
		frappe.db.count("Sidra Contract Profile", {"profile_name": PROFILE}),
	)


def manifest_file():
	return frappe.db.count(
		"File", {"attached_to_doctype": "Company", "attached_to_name": COMPANY, "file_name": MANIFEST}
	)


class TestPilotDemo(IntegrationTestCase):
	def test_guarded_twelve_month_dataset_every_module_and_repeat(self):
		ensure_base_records()
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			ensure_company(COMPANY, "SH")
			# The loader rolls back on failure; commit so its Company survives whichever test runs first.
			frappe.db.commit()
		units_before = company_units()

		# 1. Without the three staging flags nothing runs.
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 0 for flag in FLAGS}):
			gl_before = frappe.db.count("GL Entry")
			with self.assertRaisesRegex(frappe.ValidationError, "staging-only flags"):
				create_pilot_demo_data()
			self.assertEqual(frappe.db.count("GL Entry"), gl_before)

		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			# 2. A failure part way through leaves no master and no partial ledger.
			with patch("sidra_realestate.pilot_demo._finance", side_effect=RuntimeError("test rollback")):
				with self.assertRaisesRegex(RuntimeError, "test rollback"):
					create_pilot_demo_data()
			self.assertEqual(pilot_masters(), (0, 0, 0, 0, 0, 0, 0))
			self.assertEqual(manifest_file(), 0)
			self.assertEqual(frappe.db.count("GL Entry"), gl_before)
			self.assertEqual(company_units(), units_before)

			# 3. An unreadable manifest is a refusal, never a clean slate.
			with patch("sidra_realestate.pilot_demo.frappe.get_all", side_effect=RuntimeError("unreadable")):
				with self.assertRaisesRegex(frappe.ValidationError, "manifest"):
					create_pilot_demo_data()
			self.assertEqual(frappe.db.count("GL Entry"), gl_before)

			self._foreign_gl_refused(units_before)

			# 4. The real load.
			data = create_pilot_demo_data()
			self.assertTrue(data["created"])
			self._dashboard_reads_pilot_without_old_finance_manifest(data)
			self.assertEqual(manifest_file(), 1)
			self.assertEqual(company_units(), units_before, "the Company's own units must not change")

			self._every_module_is_populated(data)
			self._ledger_matches_the_plan(data)

			# 5. A rerun verifies and changes nothing.
			gl_after = frappe.db.count("GL Entry")
			again = create_pilot_demo_data()
			self.assertFalse(again["created"])
			self.assertEqual(data["vouchers"], again["vouchers"])
			self.assertEqual(data["counts"], again["counts"])
			self.assertEqual(frappe.db.count("GL Entry"), gl_after)
			self.assertEqual(company_units(), units_before)
			self.assertEqual(manifest_file(), 1)

			check = verify_pilot_demo()
			self.assertEqual(check["company"], COMPANY)

		# 6. A non-Administrator cannot run it even with the flags set.
		with patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			with as_user("sidra.manager@example.com"):
				with self.assertRaises(frappe.PermissionError):
					create_pilot_demo_data()

	def _foreign_gl_refused(self, units_before):
		"""One voucher no manifest owns: refuse, name the count, write nothing (G14)."""
		from sidra_realestate.finance_demo import _fiscal_year

		before = (frappe.db.count("GL Entry"), pilot_masters(), units_before)
		frappe.db.savepoint("pilot_foreign_gl")
		try:
			_fiscal_year(frappe.utils.getdate())
			cash = frappe.get_all(
				"Account",
				filters={"company": COMPANY, "is_group": 0, "account_type": "Cash"},
				pluck="name",
			)[0]
			equity = frappe.get_all(
				"Account",
				filters={"company": COMPANY, "is_group": 0, "root_type": "Equity"},
				pluck="name",
			)[0]
			frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"company": COMPANY,
					"voucher_type": "Journal Entry",
					"posting_date": frappe.utils.getdate(),
					"user_remark": "_Test foreign entry, not owned by any demo manifest",
					"accounts": [
						{"account": cash, "debit_in_account_currency": 1},
						{"account": equity, "credit_in_account_currency": 1},
					],
				}
			).insert().submit()
			with self.assertRaisesRegex(frappe.ValidationError, "not owned by a demo"):
				create_pilot_demo_data()
			self.assertEqual(pilot_masters(), before[1], "a refusal must write nothing")
			self.assertEqual(company_units(), before[2])
		finally:
			frappe.db.rollback(save_point="pilot_foreign_gl")
		self.assertEqual(frappe.db.count("GL Entry"), before[0])

	def _dashboard_reads_pilot_without_old_finance_manifest(self, data):
		from frappe.utils import getdate

		from sidra_realestate.api.finance_demo_snapshot import demo_financials
		from sidra_realestate.api.staff_dashboard import get_dashboard

		original = frappe.get_list

		def pilot_only(doctype, *args, **kwargs):
			rows = original(doctype, *args, **kwargs)
			if doctype in ("Sales Invoice", "Payment Entry"):
				return [row for row in rows if row.name in data["vouchers"][doctype]]
			return rows

		with (
			patch("sidra_realestate.api.finance_demo_snapshot._manifest", return_value=None),
			patch("sidra_realestate.api.finance_demo_snapshot.frappe.get_list", side_effect=pilot_only),
		):
			result = demo_financials(COMPANY, "USD", getdate(data["from_date"]), getdate(data["as_of"]))
			self.assertTrue(result["available"], result)
			self.assertGreater(Decimal(result["received"]), 0)
			self.assertGreater(Decimal(result["overdue"]), 0)
			self.assertIsNone(result["overdue_contracts"])
			dashboard = get_dashboard(company=COMPANY)
			self.assertTrue(dashboard["payments"]["available"], dashboard["payments"])
			self.assertTrue(dashboard["executive"]["metrics"]["cash_collected"]["available"])
			with as_user("sidra.manager@example.com"):
				self.assertFalse(
					demo_financials(COMPANY, "USD", getdate(data["from_date"]), getdate(data["as_of"]))[
						"available"
					]
				)

	def _every_module_is_populated(self, data):
		"""The point of the dataset: no module opens empty in front of a client."""
		counts = data["counts"]
		self.assertEqual(frappe.db.count("Sidra Scheme", {"scheme_code": ("like", PREFIX + "-%")}), 4)
		self.assertEqual(frappe.db.count("Sidra Unit", {"scheme": ("like", PREFIX + "-%")}), 120)
		self.assertEqual(frappe.db.count("Customer", {"customer_name": ("like", CUSTOMER_PREFIX + "%")}), 40)
		for doctype, filters, expected in (
			("Sidra Sale Quotation", {"company": COMPANY}, counts["quotations"]),
			("Sidra Reservation", {"company": COMPANY}, counts["reservations"]),
			("Sidra Construction Job", {"company": COMPANY}, counts["jobs"]),
		):
			with self.subTest(doctype=doctype):
				self.assertGreaterEqual(frappe.db.count(doctype, filters), expected)
		for doctype in (
			"Sidra Sale Contract",
			"Sidra Title Transfer",
			"Sidra Unit Price History",
			"Sidra Customer KYC",
			"Sidra Construction Quotation",
			"Sidra Variation Order",
		):
			with self.subTest(doctype=doctype):
				self.assertGreater(frappe.db.count(doctype), 0, f"{doctype} would open empty")

		# Both contract types and both sources, or the sales reports look uniform.
		types = set(
			frappe.get_all(
				"Sidra Sale Contract",
				filters={"company": COMPANY, "buyer_agent_name": ("like", PREFIX + "-CON-%")},
				pluck="contract_type",
			)
		)
		self.assertEqual(types, {"Cash", "Installment"})
		# Submitted and draft contracts both exist.
		statuses = set(
			frappe.get_all(
				"Sidra Sale Contract",
				filters={"buyer_agent_name": ("like", PREFIX + "-CON-%")},
				pluck="docstatus",
			)
		)
		self.assertEqual(statuses, {0, 1})

	def _ledger_matches_the_plan(self, data):
		"""Posted vouchers are exactly those the manifest claims, and the books balance."""
		for doctype in VOUCHER_TYPES:
			names = data["vouchers"][doctype]
			with self.subTest(doctype=doctype):
				self.assertTrue(names, f"{doctype} posted nothing")
				for name in names:
					self.assertEqual(frappe.db.get_value(doctype, name, "docstatus"), 1)

		owned = {name for names in data["vouchers"].values() for name in names}
		rows = frappe.get_all(
			"GL Entry",
			filters={"company": COMPANY, "is_cancelled": 0, "voucher_no": ("in", list(owned))},
			fields=["debit", "credit"],
			limit_page_length=0,
		)
		debit = sum(Decimal(str(row.debit)) for row in rows)
		credit = sum(Decimal(str(row.credit)) for row in rows)
		self.assertEqual(debit, credit, "the pilot ledger does not balance")
		self.assertGreater(debit, 0)

		expected = data["expected_totals"]
		outstanding = frappe.get_all(
			"Sales Invoice",
			filters={"company": COMPANY, "docstatus": 1, "customer": ("like", CUSTOMER_PREFIX + "%")},
			pluck="outstanding_amount",
		)
		self.assertEqual(
			Decimal(str(sum(outstanding))).quantize(Decimal("0.01")),
			Decimal(expected["receivables"]),
			"receivables must match the plan, or the AR report contradicts the demo script",
		)
		# Paid, part paid and open invoices all present, so AR ageing is not a single bucket.
		self.assertTrue(any(value == 0 for value in outstanding))
		self.assertTrue(any(value > 0 for value in outstanding))
