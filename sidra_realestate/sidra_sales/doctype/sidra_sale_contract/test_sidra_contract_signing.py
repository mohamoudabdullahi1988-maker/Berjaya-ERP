# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Parties, signed-copy gate, frozen clauses and the contract print (SAL-19, SAL-20, INS-21; issue #8)."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.install import ensure_contract_clauses, ensure_contract_profiles
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import revise_draft
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	GENERAL_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	make_held_profile,
	make_scheme,
	make_unit,
	private_file,
	signing_values,
	unique,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sidra Unit", "Customer", "Company", "Sidra Contract Profile", "User"]


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
		attach = values.pop("attach", True)
		doc.update(values)
		doc = frappe.get_doc(doc).insert(ignore_permissions=True)
		return attach_signed_copy(doc) if attach else doc

	def assert_submit_refused(self, doc, *fragments):
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)) as caught:
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
		doc = self.contract(attach=False, notary_name=None, notary_reference=None, parties=[])
		self.assert_submit_refused(
			doc,
			"signed copy",
			"notary",
			"notary reference",
			"one Seller",
			"Seller Guarantor",
			"two Witnesses",
		)

	def test_signed_copy_must_be_private(self):
		doc = self.contract(attach=False)
		attach_signed_copy(doc, is_private=0)
		self.assert_submit_refused(doc, "private")

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
		self.contract(
			parties=[seller, guarantor, w1, w2, {**w2, "full_name": "_Test Witness Three"}]
		).submit()

	def test_only_guarantor_pledges_property(self):
		seller, guarantor, w1, w2 = signing_values()["parties"]
		with self.assertRaises(frappe.ValidationError):
			self.contract(parties=[{**seller, "pledged_property": "x"}, guarantor, w1, w2])

	def test_notary_reference_unique_among_signed_contracts(self):
		first = self.contract()
		first.submit()
		second = self.contract(notary_reference=first.notary_reference)
		self.assert_submit_refused(second, first.name)

	def test_legal_hold_is_reported_before_missing_signatures(self):
		doc = self.contract(profile=make_held_profile().name, attach=False, parties=[])
		self.assert_submit_refused(doc, "legal hold")

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

		profile.reload()
		profile.clauses = profile.clauses[:1]
		profile.save(ignore_permissions=True)

		doc.reload()
		doc.submit()
		self.assertEqual([row.clause for row in doc.clauses], [c1.name, c2.name])

		frappe.db.set_value("Sidra Contract Clause", c1.name, "text_en", "Changed after signing.")
		doc.reload()
		self.assertEqual(doc.clauses[0].text_en, "A test clause.")  # signed snapshot preserved

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
			row = frappe.db.get_value(
				"Sidra Contract Clause", code, ["approved", "text_so", "text_en"], as_dict=True
			)
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
		for expected in (
			"Qodobka la doortay.",
			"The chosen clause.",
			"_Test Witness Two",
			"_Test pledged plot 1",
		):
			self.assertIn(expected, html)
		self.assertNotIn("Qodob kale.", html)
		self.assertNotIn(other.text_en, html)
		self.assertNotIn("Draft for signing", html)
		self.assertIn(doc.notary_reference, html)
		self.assertEqual(html.count("<tr><td>1</td>"), 1)  # schedule printed once

	def test_amounts_print_in_the_company_currency(self):
		"""Review follow-up: money fields named "USD" as a field, so amounts printed in the site default."""
		doc = self.contract()
		doc.submit()
		self.assertEqual(doc.currency, "USD")
		html = frappe.get_print("Sidra Sale Contract", doc.name, print_format="Sidra Sale Contract", doc=doc)
		self.assertIn("$ 10,000.00", html)
		self.assertNotIn("₹", html)
		self.assertIn("$", doc.schedule[0].get_formatted("amount", doc))

	def test_contract_pdf_is_generated(self):
		"""Actual PDF output through the print format's generator (Chrome)."""
		from io import BytesIO

		from pypdf import PdfReader

		doc = self.contract(profile=self.profile([self.clause(text_en="PDF clause text.")]).name)
		doc.submit()
		pdf = frappe.get_print(
			"Sidra Sale Contract", doc.name, print_format="Sidra Sale Contract", as_pdf=True
		)
		self.assertTrue(pdf.startswith(b"%PDF"))
		text = " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
		self.assertIn("PDF clause text.", text)
		self.assertIn("1,000.00", text)

	def test_print_escapes_entered_text(self):
		doc = self.contract(buyer_agent_name="<script>alert(1)</script>")
		html = frappe.get_print("Sidra Sale Contract", doc.name, print_format="Sidra Sale Contract", doc=doc)
		self.assertNotIn("<script>alert(1)</script>", html)
		self.assertIn("Draft for signing", html)

	def test_signed_copy_url_is_private(self):
		self.assertTrue(private_file().startswith("/private/files/"))

	# ------------------------------------------------------------ review finding 1: signed copy ownership
	def test_unattached_private_file_is_refused(self):
		"""A private file uploaded elsewhere (not to this contract) cannot be the signed copy."""
		doc = self.contract(attach=False)
		stray = frappe.get_doc(
			{"doctype": "File", "file_name": unique("stray") + ".txt", "content": b"stray", "is_private": 1}
		).insert(ignore_permissions=True)
		frappe.db.set_value("File", stray.name, "owner", OUTSIDER)  # someone else's upload
		doc.signed_copy = stray.file_url
		doc.save(ignore_permissions=True)  # Frappe links a new File record to this contract
		self.assert_submit_refused(doc, "another record")

	def test_another_contracts_signed_copy_is_refused(self):
		first = self.contract()
		second = self.contract(attach=False)
		second.signed_copy = first.signed_copy
		second.save(ignore_permissions=True)
		# refused either as not attached to this contract or as shared with another record
		self.assert_submit_refused(second)
		first.submit()  # the rightful owner is unaffected

	def test_signed_copy_must_be_saved_before_submit(self):
		doc = self.contract(attach=False)
		other = self.contract()
		doc.signed_copy = other.signed_copy  # set in the same call as submit, never saved
		self.assert_submit_refused(doc, "")
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 0)

	def test_submitter_must_be_able_to_read_the_signed_copy(self):
		doc = self.contract()
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc("Sidra Sale Contract", doc.name)
			from unittest.mock import patch

			with (
				patch("frappe.core.doctype.file.file.File.has_permission", return_value=False),
				self.assertRaises(frappe.PermissionError),
			):
				doc.submit()

	def test_signed_copy_missing_on_disk_is_refused(self):
		doc = self.contract()
		from unittest.mock import patch

		with patch("frappe.core.doctype.file.file.File.exists_on_disk", return_value=False):
			self.assert_submit_refused(doc, "missing from the server")

	def test_sales_manager_submits_with_own_upload(self):
		with as_user(SALES_MANAGER):
			doc = self.contract()
			doc = frappe.get_doc("Sidra Sale Contract", doc.name)
			doc.submit()
		self.assertEqual(frappe.db.get_value("Sidra Sale Contract", doc.name, "docstatus"), 1)

	# ------------------------------------------------------------ review finding 3: notary reference
	def test_notary_reference_whitespace_is_normalised(self):
		doc = self.contract(notary_reference="  IPN/HL/ 077 /2031 ")
		self.assertEqual(doc.notary_reference, "IPN/HL/077/2031")
		doc.submit()
		self.assertEqual(doc.notary_reference_key, "IPN/HL/077/2031")
		twin = self.contract(notary_reference="IPN/HL/077/ 2031")
		self.assert_submit_refused(twin, doc.name)

	def test_drafts_may_share_a_reference_until_signed(self):
		a = self.contract(notary_reference="IPN/HL/078/2031")
		b = self.contract(notary_reference="IPN/HL/078/2031")
		self.assertIsNone(a.notary_reference_key)
		self.assertIsNone(b.notary_reference_key)
		a.submit()
		self.assert_submit_refused(b, a.name)

	def test_database_index_rejects_duplicate_even_without_the_check(self):
		a = self.contract(notary_reference="IPN/HL/079/2031")
		a.submit()
		b = self.contract(notary_reference="IPN/HL/079/2031")
		from unittest.mock import patch

		path = (
			"sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract.frappe.db.get_value"
		)
		real = frappe.db.get_value

		def no_duplicate_lookup(doctype, filters=None, *args, **kwargs):
			if isinstance(filters, dict) and "notary_reference_key" in filters:
				return None
			return real(doctype, filters, *args, **kwargs)

		with patch(path, side_effect=no_duplicate_lookup), self.assertRaises(frappe.UniqueValidationError):
			b.submit()

	# ------------------------------------------------------------ review finding 5: clause approval and revision
	def test_approving_clause_later_unblocks_existing_draft(self):
		pending = self.clause(approved=False)
		doc = self.contract(profile=self.profile([pending]).name)
		self.assertEqual(doc.clauses[0].approved, 0)
		self.assert_submit_refused(doc, pending.name)

		with as_user(GENERAL_MANAGER):
			clause = frappe.get_doc("Sidra Contract Clause", pending.name)
			clause.approved = 1
			clause.save()

		doc = frappe.get_doc("Sidra Sale Contract", doc.name)
		doc.submit()
		self.assertEqual(doc.clauses[0].approved, 1)  # approval recorded at signing

	def test_revoked_approval_blocks_draft_frozen_as_approved(self):
		clause = self.clause()
		doc = self.contract(profile=self.profile([clause]).name)
		self.assertEqual(doc.clauses[0].approved, 1)
		frappe.db.set_value("Sidra Contract Clause", clause.name, "approved", 0)
		self.assert_submit_refused(doc, clause.name)

	def test_changed_wording_needs_a_revised_draft(self):
		clause = self.clause()
		profile = self.profile([clause])
		old = self.contract(profile=profile.name, notary_reference="IPN/HL/081/2031")
		frappe.db.set_value("Sidra Contract Clause", clause.name, "text_en", "Reworded and re-approved.")

		with self.assertRaises(frappe.ValidationError) as caught:
			frappe.get_doc("Sidra Sale Contract", old.name).submit()
		self.assertIn("Revise Draft", str(caught.exception))

		new_name = revise_draft(old.name)
		new = frappe.get_doc("Sidra Sale Contract", new_name)
		self.assertEqual(new.docstatus, 0)
		self.assertEqual(new.clauses[0].text_en, "Reworded and re-approved.")
		self.assertIsNone(new.signed_copy)  # signed afresh
		self.assertEqual([p.full_name for p in new.parties], [p.full_name for p in old.parties])
		self.assertEqual(new.units[0].unit, old.units[0].unit)

		old.reload()
		self.assertEqual(old.clauses[0].text_en, "A test clause.")  # old draft untouched
		comments = frappe.get_all(
			"Comment", filters={"reference_name": old.name, "comment_type": "Info"}, pluck="content"
		)
		self.assertTrue(any(new_name in c for c in comments))

		attach_signed_copy(new).submit()
		self.assertEqual(new.docstatus, 1)

	def test_signed_contract_cannot_be_revised(self):
		doc = self.contract()
		doc.submit()
		with self.assertRaises(frappe.ValidationError):
			revise_draft(doc.name)

	def test_revise_draft_needs_write_permission(self):
		doc = self.contract()
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			revise_draft(doc.name)
