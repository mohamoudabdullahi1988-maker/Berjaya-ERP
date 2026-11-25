# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Buyer KYC and the contract gate (SAL-07; decision G12; docs/KYC-AND-TITLE_v0.1.md §2)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	ensure_contract_settings,
)
from sidra_realestate.sidra_sales.doctype.sidra_customer_kyc.sidra_customer_kyc import (
	has_verified_kyc,
	verify_kyc,
)
from sidra_realestate.tests.helpers import (
	COMPANY,
	GENERAL_MANAGER,
	NO_KYC_BUYER,
	OTHER_SALES_MANAGER,
	OUTSIDER,
	PROJECT_MANAGER,
	SALES_MANAGER,
	SALES_USER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	ensure_customer,
	make_confirmed_contract,
	make_scheme,
	make_unit,
	private_file,
	signing_values,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Company", "User", "Sidra Unit", "Sidra Contract Profile"]

KYC = "Sidra Customer KYC"


class TestSidraCustomerKYC(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def kyc(self, user=SALES_USER, scan=True, **values):
		"""Entered by sales staff for a new synthetic customer, with the scanned ID uploaded."""
		customer = ensure_customer(unique("_Test KYC Buyer"))
		with as_user(user):
			doc = frappe.get_doc(
				{
					"doctype": KYC,
					"customer": customer,
					"id_type": "Passport",
					"id_number": " P-0012345 ",
					"phone": "+252 63 000 0200",
					"address": "_Test street, Hargeisa",
					**values,
				}
			).insert()
			if scan:
				doc.id_document = private_file(name="passport.pdf", attached_to=doc, field="id_document")
				doc.save()
		return doc

	def verify(self, doc, user=OTHER_SALES_MANAGER):
		with as_user(user):
			return verify_kyc(doc.name)

	def test_sales_enters_manager_verifies(self):
		doc = self.kyc()
		self.assertEqual((doc.status, doc.id_number, doc.name), ("Draft", "P-0012345", doc.customer))
		self.assertFalse(has_verified_kyc(doc.customer))
		self.assertEqual(self.verify(doc)["verified_by"], OTHER_SALES_MANAGER)
		self.assertTrue(has_verified_kyc(doc.customer))
		with self.assertRaises(frappe.ValidationError):
			self.verify(doc)  # already verified

	def test_only_sales_manager_verifies(self):
		doc = self.kyc()
		for user in (SALES_USER, GENERAL_MANAGER):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				self.verify(doc, user=user)

	def test_scan_required_private_and_own(self):
		with self.assertRaises(frappe.ValidationError):
			self.verify(self.kyc(scan=False))
		doc = self.kyc(scan=False)
		doc.id_document = private_file(name="public.pdf", attached_to=doc, field="id_document", is_private=0)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		other = self.kyc()
		borrowed = self.kyc(scan=False)
		borrowed.id_document = other.id_document
		borrowed.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.verify(borrowed)

	def test_change_after_verification_needs_verifying_again(self):
		doc = self.kyc()
		self.verify(doc)
		doc.reload()
		doc.phone = "+252 63 000 0999"
		doc.save(ignore_permissions=True)
		self.assertEqual((doc.status, doc.verified_by), ("Draft", None))
		self.assertFalse(has_verified_kyc(doc.customer))

	def test_verification_cannot_be_forged(self):
		doc = self.kyc(status="Verified", verified_by=SALES_USER)
		self.assertEqual((doc.status, doc.verified_by), ("Draft", None))
		doc.status = "Verified"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "Draft")

	def test_one_record_per_customer_and_required_details(self):
		doc = self.kyc()
		with self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError)):
			frappe.get_doc(
				{
					"doctype": KYC,
					"customer": doc.customer,
					"id_type": "Passport",
					"id_number": "X",
					"phone": "1",
					"address": "a",
				}
			).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.kyc(address="   ")
		with self.assertRaises(frappe.ValidationError):
			self.kyc(guarantor_id_number="G-1")  # guarantor without name and phone
		self.assertEqual(
			self.kyc(guarantor_name="_Test Guarantor", guarantor_phone="+252 63 1").status, "Draft"
		)

	def test_restricted_roles(self):
		doc = self.kyc()
		for user in (OUTSIDER, PROJECT_MANAGER):
			with self.subTest(user=user), as_user(user):
				self.assertFalse(frappe.has_permission(KYC, "read", doc=doc.name))
				with self.assertRaises(frappe.PermissionError):
					frappe.get_list(KYC, filters={"name": doc.name})
		with as_user(GENERAL_MANAGER):
			self.assertTrue(frappe.has_permission(KYC, "read", doc=doc.name))
			self.assertFalse(frappe.has_permission(KYC, "write", doc=doc.name))
		for role in ("System Manager", "Sidra Finance Reviewer", "Sidra Inspector"):
			self.assertNotIn(role, [p.role for p in frappe.get_meta(KYC).permissions])

	# ------------------------------------------------------------ contract gate (G12)
	def generated_contract(self, customer):
		unit = make_unit(unique("_T-KYC"), make_scheme("_TEST-KYC")).name
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"customer": customer,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"contract_profile": "Profile A",
				"agreed_price": 10000,
				"units": [{"unit": unit, "allocated_price": 10000}],
				**signing_values(),
			}
		).insert(ignore_permissions=True)
		return attach_signed_copy(doc)

	def test_generated_contract_needs_verified_kyc(self):
		make_confirmed_contract("_TEST-KYC")  # the base buyer has verified KYC
		doc = self.generated_contract(NO_KYC_BUYER)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		self.assertIn("KYC", str(caught.exception))

	def test_registered_contract_does_not_need_kyc(self):
		ensure_contract_settings()
		unit = make_unit(unique("_T-KYC"), make_scheme("_TEST-KYC")).name
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": "External (registered)",
				"external_reference": unique("KYC-EXT"),
				"customer": NO_KYC_BUYER,
				"company": COMPANY,
				"signed_on": "2026-01-15",
				"agreed_price": 3000,
				"units": [{"unit": unit, "allocated_price": 3000}],
				"schedule": [{"row_type": "Installment", "due_date": "2026-02-10", "amount": 3000}],
			}
		).insert(ignore_permissions=True)
		attach_signed_copy(doc)
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc("Sidra Sale Contract", doc.name)
			doc.submit()
		self.assertEqual(doc.docstatus, 1)
