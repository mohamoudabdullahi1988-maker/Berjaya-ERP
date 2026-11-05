# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Parties, signed-copy gate, frozen clauses and the contract print (SAL-19, SAL-20, INS-21; issue #8)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.install import ensure_contract_clauses, ensure_contract_profiles
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	ensure_base_records,
	make_scheme,
	make_unit,
	private_file,
	signing_values,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Customer", "Company", "Sidra Contract Profile"]


class TestContractSigning(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		ensure_contract_clauses()
		cls.scheme = make_scheme("_TEST-SIGN")

	def clause(self, approved=True, active=True, text_so="Qodob tijaabo ah.", text_en="A test clause."):
		return frappe.get_doc(
			{
				"doctype": "Sidra Contract Clause",
				"clause_code": unique("_T-CL"),
				"title": "_Test clause",
				"text_so": text_so,
				"text_en": text_en,
				"approved": int(approved),
				"active": int(active),
			}
		).insert(ignore_permissions=True)

	def profile(self, clauses):
		return frappe.get_doc(
			{
				"doctype": "Sidra Contract Profile",
				"profile_name": unique("_Test Clause Profile"),
				"installments": 10,
				"due_day": 5,
				"title_deadline_days": 20,
				"clauses": [{"clause": c.name} for c in clauses],
			}
		).insert(ignore_permissions=True)

	def contract(self, profile="Profile A", **values):
		unit = make_unit(unique("_T-SIGN"), self.scheme).name
		doc = {
			"doctype": "Sidra Sale Contract",
			"contract_type": "Installment",
			"customer": BUYER,
			"company": COMPANY,
			"signed_on": "2026-11-05",
			"contract_profile": profile,
			"agreed_price": 10000,
			"units": [{"unit": unit, "allocated_price": 10000}],
			**signing_values(),
		}
		doc.update(values)
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def assert_submit_refused(self, doc, *fragments):
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		for fragment in fragments:
			self.assertIn(fragment, str(caught.exception))
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 0)

	# ------------------------------------------------------------ signed-copy gate
	def test_complete_contract_submits(self):
		doc = self.contract()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(len(doc.parties), 4)

	def test_bare_draft_can_be_saved_but_not_submitted(self):
		doc = self.contract(signed_copy=None, notary_name=None, notary_reference=None, parties=[])
		self.assert_submit_refused(
			doc, "signed copy", "notary", "notary reference", "one Seller", "Seller Guarantor", "two Witnesses"
		)

	def test_signed_copy_must_be_private(self):
		public = frappe.get_doc(
			{"doctype": "File", "file_name": unique("public") + ".txt", "content": b"public scan", "is_private": 0}
		).insert(ignore_permissions=True)
		self.assert_submit_refused(self.contract(signed_copy=public.file_url), "private")

	def test_party_rules(self):
		base = signing_values()["parties"]
		seller, guarantor, w1, w2 = base
		cases = [
			([guarantor, w1, w2], "one Seller"),
			([seller, seller, guarantor, w1, w2], "one Seller"),
			([seller, w1, w2], "Seller Guarantor"),
			([seller, {**guarantor, "pledged_property": ""}, w1, w2], "Seller Guarantor"),
			([seller, guarantor, w1], "two Witnesses"),
			([seller, guarantor, w1, {**w2, "phone": ""}], "two Witnesses"),
		]
		for parties, fragment in cases:
			with self.subTest(fragment=fragment, rows=len(parties)):
				self.assert_submit_refused(self.contract(parties=parties), fragment)
		self.contract(parties=[seller, guarantor, w1, w2, {**w2, "full_name": "_Test Witness Three"}]).submit()

	def test_only_guarantor_pledges_property(self):
		seller, guarantor, w1, w2 = signing_values()["parties"]
		with self.assertRaises(frappe.ValidationError):
			self.contract(parties=[{**seller, "pledged_property": "x"}, guarantor, w1, w2])

	def test_notary_reference_unique_among_signed_contracts(self):
		first = self.contract()
		first.submit()
		second = self.contract(notary_reference=first.notary_reference)
		self.assert_submit_refused(second, first.name)

	def test_cash_contract_has_the_same_gate(self):
		unit = make_unit(unique("_T-SIGN"), self.scheme).name
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Cash",
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-11-05",
				"agreed_price": 5000,
				"units": [{"unit": unit, "allocated_price": 5000}],
			}
		).insert(ignore_permissions=True)
		self.assert_submit_refused(doc, "signed copy")
		self.assertEqual(frappe.db.get_value("Sidra Unit", unit, "status"), "Available")

	# ------------------------------------------------------------ clauses
	def test_clauses_frozen_from_profile(self):
		c1, c2 = self.clause(), self.clause()
		profile = self.profile([c1, c2])
		doc = self.contract(profile=profile.name)
		self.assertEqual([row.clause for row in doc.clauses], [c1.name, c2.name])
		self.assertEqual(doc.clauses[0].text_so, "Qodob tijaabo ah.")

		frappe.db.set_value("Sidra Contract Clause", c1.name, "text_en", "Changed later.")
		profile.reload()
		profile.clauses = profile.clauses[:1]
		profile.save(ignore_permissions=True)

		doc.reload()
		doc.submit()
		self.assertEqual([row.clause for row in doc.clauses], [c1.name, c2.name])
		self.assertEqual(doc.clauses[0].text_en, "A test clause.")

	def test_clause_lines_cannot_be_edited(self):
		doc = self.contract(profile=self.profile([self.clause()]).name)
		doc.clauses[0].text_en = "Edited"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		doc.reload()
		doc.clauses = []
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_unapproved_clause_blocks_submit(self):
		pending = self.clause(approved=False, text_so="", text_en="")
		doc = self.contract(profile=self.profile([pending]).name)
		self.assert_submit_refused(doc, pending.name)

	def test_inactive_clause_on_profile_blocks_new_contract(self):
		profile = self.profile([self.clause(active=False)])
		with self.assertRaises(frappe.ValidationError):
			self.contract(profile=profile.name)

	def test_cash_contract_takes_no_clauses(self):
		unit = make_unit(unique("_T-SIGN"), self.scheme).name
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Sidra Sale Contract",
					"contract_type": "Cash",
					"customer": BUYER,
					"company": COMPANY,
					"signed_on": "2026-11-05",
					"agreed_price": 5000,
					"units": [{"unit": unit, "allocated_price": 5000}],
					"clauses": [{"clause": "RESTRICTIONS", "title": "x", "approved": 1}],
				}
			).insert(ignore_permissions=True)

	def test_seeded_clauses_have_no_wording_and_are_not_on_profiles(self):
		for code in ("RESTRICTIONS", "INSOLVENCY", "TITLE-COSTS", "BEACON", "FIRST-RIGHT"):
			row = frappe.db.get_value("Sidra Contract Clause", code, ["approved", "text_so", "text_en"], as_dict=True)
			self.assertEqual((row.approved, row.text_so, row.text_en), (0, None, None))
		for profile in ("Profile A", "Profile B"):
			self.assertEqual(frappe.get_doc("Sidra Contract Profile", profile).clauses, [])

	# ------------------------------------------------------------ print (INS-21)
	def test_print_shows_only_this_contracts_clauses_in_both_languages(self):
		chosen = self.clause(text_so="Qodobka la doortay.", text_en="The chosen clause.")
		other = self.clause(text_so="Qodob kale.", text_en="Another clause.")
		doc = self.contract(profile=self.profile([chosen]).name)
		doc.submit()

		html = frappe.get_print("Sidra Sale Contract", doc.name, print_format="Sidra Sale Contract", doc=doc)
		for expected in ("Qodobka la doortay.", "The chosen clause.", "_Test Witness Two", "_Test pledged plot 1"):
			self.assertIn(expected, html)
		self.assertNotIn("Qodob kale.", html)
		self.assertNotIn(other.text_en, html)
		self.assertNotIn("Draft for signing", html)
		self.assertIn(doc.notary_reference, html)
		self.assertEqual(html.count("<tr><td>1</td>"), 1)  # schedule printed once

	def test_print_escapes_entered_text(self):
		doc = self.contract(buyer_agent_name="<script>alert(1)</script>")
		html = frappe.get_print("Sidra Sale Contract", doc.name, print_format="Sidra Sale Contract", doc=doc)
		self.assertNotIn("<script>alert(1)</script>", html)
		self.assertIn("Draft for signing", html)

	def test_signed_copy_url_is_private(self):
		self.assertTrue(private_file().startswith("/private/files/"))
