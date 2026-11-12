# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Title transfer tracker (SAL-08, SAL-18; decision G12; docs/KYC-AND-TITLE_v0.1.md §3)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from sidra_realestate.sidra_sales.doctype.sidra_title_transfer.sidra_title_transfer import (
	confirm_final_payment,
	confirm_handover,
	refresh_title_states,
)
from sidra_realestate.tests.helpers import (
	GENERAL_MANAGER,
	OTHER_SALES_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	ensure_base_records,
	make_confirmed_contract,
	make_scheme,
	make_unit,
	private_file,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Company", "User", "Sidra Unit", "Sidra Contract Profile"]

TITLE = "Sidra Title Transfer"
SCHEME = "_TEST-TTL"


class TestSidraTitleTransfer(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def title(self, paid_days_ago=None, evidence=True, **values):
		"""Opened by a Sales Manager for a confirmed Profile A contract (20-day title deadline)."""
		contract = make_confirmed_contract(SCHEME)
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc(
				{"doctype": TITLE, "contract": contract.name, "unit": contract.units[0].unit, **values}
			).insert()
			if paid_days_ago is not None:
				doc.final_payment_date = add_days(today(), -paid_days_ago)
				if evidence:
					doc.final_payment_evidence = private_file(
						name="receipt.pdf", attached_to=doc, field="final_payment_evidence"
					)
				doc.save()
		return doc

	def confirm_payment(self, doc, user=OTHER_SALES_MANAGER):
		with as_user(user):
			confirm_final_payment(doc.name)
		doc.reload()
		return doc

	def enter_handover(self, doc, on=None, **values):
		with as_user(SALES_MANAGER):
			doc.reload()
			doc.update(
				{
					"deed_number": "DEED-0001",
					"handed_over_on": on or today(),
					"handed_over_to": "_Test Buyer Amina",
					"handover_evidence": private_file(
						name="handover.pdf", attached_to=doc, field="handover_evidence"
					),
					**values,
				}
			)
			doc.save()
		return doc

	def handover(self, doc, user=GENERAL_MANAGER):
		with as_user(user):
			confirm_handover(doc.name)
		doc.reload()
		return doc

	# ------------------------------------------------------------ record
	def test_follows_contract(self):
		doc = self.title()
		contract = frappe.get_doc("Sidra Sale Contract", doc.contract)
		self.assertEqual((doc.customer, doc.company), (contract.customer, contract.company))
		self.assertEqual(
			(doc.title_deadline_days, doc.status, doc.deadline_date), (20, "Awaiting Final Payment", None)
		)
		self.assertIn("Per Day", doc.title_term)

	def test_contract_must_be_confirmed_and_hold_the_unit(self):
		contract = make_confirmed_contract(SCHEME)
		other_unit = make_unit(unique("_T-TTL"), make_scheme(SCHEME)).name
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": TITLE, "contract": contract.name, "unit": other_unit}).insert(
				ignore_permissions=True
			)
		values = {"doctype": TITLE, "contract": contract.name, "unit": contract.units[0].unit}
		frappe.get_doc(values).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(values).insert(ignore_permissions=True)  # one record per contract and unit

	def test_who_can_open_a_record(self):
		contract = make_confirmed_contract(SCHEME)
		values = {"doctype": TITLE, "contract": contract.name, "unit": contract.units[0].unit}
		for user in (SALES_USER, GENERAL_MANAGER, OUTSIDER):
			with self.subTest(user=user), as_user(user), self.assertRaises(frappe.PermissionError):
				frappe.get_doc(values).insert()

	# ------------------------------------------------------------ final payment and deadline (SAL-18)
	def test_second_sales_manager_confirms_final_payment(self):
		doc = self.title(paid_days_ago=3)
		self.assertEqual(
			(doc.final_payment_entered_by, doc.status), (SALES_MANAGER, "Awaiting Final Payment")
		)
		with self.assertRaises(frappe.PermissionError):
			self.confirm_payment(doc, user=SALES_MANAGER)  # entered it
		with self.assertRaises(frappe.PermissionError):
			self.confirm_payment(doc, user=GENERAL_MANAGER)
		doc = self.confirm_payment(doc)
		self.assertEqual(doc.final_payment_confirmed_by, OTHER_SALES_MANAGER)
		self.assertEqual(getdate(doc.deadline_date), getdate(add_days(today(), 17)))
		self.assertEqual((doc.status, doc.days_overdue), ("In Progress", 0))

	def test_evidence_required_private_and_own(self):
		with self.assertRaises(frappe.ValidationError):
			self.confirm_payment(self.title(paid_days_ago=3, evidence=False))
		with self.assertRaises(frappe.ValidationError):
			self.confirm_payment(self.title())  # no date
		doc = self.title(paid_days_ago=3, evidence=False)
		doc.final_payment_evidence = private_file(
			name="public.pdf", attached_to=doc, field="final_payment_evidence", is_private=0
		)
		doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.confirm_payment(doc)

	def test_confirmed_payment_is_frozen_and_cannot_be_forged(self):
		doc = self.title(
			final_payment_confirmed_by=SALES_MANAGER, final_payment_confirmed_on=today(), status="Handed Over"
		)
		self.assertEqual((doc.final_payment_confirmed_by, doc.status), (None, "Awaiting Final Payment"))
		doc = self.confirm_payment(self.title(paid_days_ago=3))
		doc.final_payment_date = add_days(today(), -1)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		doc.reload()
		with self.assertRaises(frappe.ValidationError):
			doc.delete(ignore_permissions=True)

	def test_dates_checked(self):
		with self.assertRaises(frappe.ValidationError):
			self.title(paid_days_ago=-1)  # in the future
		with self.assertRaises(frappe.ValidationError):
			self.title(final_payment_date="2026-11-01")  # before the contract date (5 Nov 2026)
		doc = self.title(paid_days_ago=2)
		with self.assertRaises(frappe.ValidationError):
			self.enter_handover(doc, on=add_days(today(), -3))  # before the final payment

	def test_due_soon_overdue_and_daily_refresh(self):
		doc = self.confirm_payment(self.title(paid_days_ago=1))
		self.assertEqual(doc.status, "In Progress")
		doc.set_state(on_date=add_days(today(), 14))  # 5 days before the deadline
		self.assertEqual((doc.status, doc.days_overdue), ("Due Soon", 0))
		doc.set_state(on_date=add_days(today(), 22))  # 3 days after it
		self.assertEqual((doc.status, doc.days_overdue), ("Overdue", 3))
		frappe.db.set_value(TITLE, doc.name, {"status": "Overdue", "days_overdue": 9})
		refresh_title_states()
		self.assertEqual(
			tuple(frappe.db.get_value(TITLE, doc.name, ["status", "days_overdue"])), ("In Progress", 0)
		)

	# ------------------------------------------------------------ handover (SAL-08)
	def test_general_manager_confirms_handover_record_only(self):
		doc = self.confirm_payment(
			self.title(paid_days_ago=2, documents=[{"document": "Sale contract copy", "received": 1}])
		)
		unit_before = frappe.db.get_value("Sidra Unit", doc.unit, "status")
		doc = self.enter_handover(doc, submitted_on=add_days(today(), -1), land_office_reference="LO-77")
		self.assertEqual(doc.handover_entered_by, SALES_MANAGER)
		with self.assertRaises(frappe.PermissionError):
			self.handover(doc, user=OTHER_SALES_MANAGER)
		doc = self.handover(doc)
		self.assertEqual(
			(doc.status, doc.days_overdue, doc.handover_confirmed_by), ("Handed Over", 0, GENERAL_MANAGER)
		)
		self.assertEqual(
			frappe.db.get_value("Sidra Unit", doc.unit, "status"), unit_before
		)  # rule 3: record only
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.contract, "docstatus"), 1)
		doc.deed_number = "DEED-9999"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)  # locked after the handover

	def test_handover_needs_confirmed_payment_and_details(self):
		doc = self.title(paid_days_ago=2)
		with self.assertRaises(frappe.ValidationError):
			self.handover(self.enter_handover(doc))  # final payment not confirmed
		doc = self.confirm_payment(self.title(paid_days_ago=2))
		with self.assertRaises(frappe.ValidationError):
			self.handover(doc)  # nothing entered
		with self.assertRaises(frappe.ValidationError):
			self.handover(self.enter_handover(doc, deed_number=""))

	def test_document_rows_checked(self):
		with self.assertRaises(frappe.ValidationError):
			self.title(documents=[{"document": "ID copy", "received_on": today()}])  # date without Received
		with self.assertRaises(frappe.ValidationError):
			self.title(documents=[{"document": "ID copy", "file": private_file(name="p.pdf", is_private=0)}])
