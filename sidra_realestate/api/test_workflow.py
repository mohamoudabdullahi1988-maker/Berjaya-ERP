# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Workflow timeline API: stage states derived from saved records, per user, with no writes."""

import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.api.workflow import (
	BLOCKED,
	COMPLETED,
	CURRENT,
	EXTERNAL_REGISTRATION,
	PENDING,
	PROCESSES,
	STATES,
	UNAVAILABLE,
	get_contract_timeline,
)
from sidra_realestate.install import ensure_contract_profiles
from sidra_realestate.sidra_sales.doctype.sidra_contract_settings.sidra_contract_settings import (
	ensure_contract_settings,
)
from sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract import EXTERNAL
from sidra_realestate.tests.helpers import (
	BUYER,
	COMPANY,
	GENERAL_MANAGER,
	OUTSIDER,
	SALES_MANAGER,
	SALES_USER,
	SYSTEM_ONLY,
	as_user,
	attach_signed_copy,
	ensure_base_records,
	ensure_customer,
	ensure_user,
	make_confirmed_contract,
	make_held_profile,
	make_scheme,
	make_unit,
	unique,
)

FINANCE_REVIEWER = "sidra.finance-reviewer@example.com"
KEYS = [key for key, _label, _check in PROCESSES[EXTERNAL_REGISTRATION]]
WRITE = re.compile(r"^\s*(insert|update|delete|replace|alter|create|drop|truncate)\b", re.I)


class TestWorkflowTimeline(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()
		ensure_contract_profiles()
		ensure_contract_settings()
		ensure_user(FINANCE_REVIEWER, ["Sidra Finance Reviewer"])
		cls.scheme = make_scheme("_TEST-WFL")

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Sidra Contract Settings", "schedule_tolerance", 5)

	# ------------------------------------------------------------ builders
	def unit(self):
		return make_unit(unique("_T-WFL"), self.scheme).name

	def external(self, price=10000, schedule_total=None, *, attach=True, rows=True, **values):
		amount = price if schedule_total is None else schedule_total
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": EXTERNAL,
				"customer": BUYER,
				"company": COMPANY,
				"signed_on": "2026-01-15",
				"agreed_price": price,
				"units": [{"unit": self.unit(), "allocated_price": price}],
				"external_reference": unique("EXT-WFL"),
				"schedule": [{"row_type": "Installment", "due_date": "2026-02-10", "amount": amount}]
				if rows
				else [],
				**values,
			}
		).insert(ignore_permissions=True)
		return attach_signed_copy(doc) if attach else doc

	def buyer_without_kyc(self):
		return ensure_customer(unique("_Test Buyer WFL"))

	def confirm(self, doc):
		with as_user(SALES_MANAGER):
			doc = frappe.get_doc("Sidra Sale Contract", doc.name)
			doc.submit()
		return doc

	def timeline(self, doc, user=SALES_MANAGER):
		with as_user(user):
			return get_contract_timeline(doc.name)

	def states(self, result):
		return [stage["state"] for stage in result["stages"]]

	def stage(self, result, key):
		return next(stage for stage in result["stages"] if stage["key"] == key)

	def assert_stopped_at(self, result, key, state):
		"""Everything before `key` is completed, `key` has `state`, everything after is pending."""
		at = KEYS.index(key)
		expected = [COMPLETED] * at + [state] + [PENDING] * (len(KEYS) - at - 1)
		self.assertEqual(self.states(result), expected)

	# ------------------------------------------------------------ shape
	def test_shape_and_single_active_stage(self):
		result = self.timeline(self.external())
		self.assertTrue(result["supported"])
		self.assertEqual(result["transaction"]["process"], EXTERNAL_REGISTRATION)
		self.assertEqual(result["transaction"]["status"], "Draft")
		self.assertEqual([stage["key"] for stage in result["stages"]], KEYS)
		for stage in result["stages"]:
			self.assertIn(stage["state"], STATES)
			for field in ("label", "responsible", "timestamp", "record", "blocker", "allowed_actions"):
				self.assertIn(field, stage)
			self.assertEqual(stage["blocker"] is not None, stage["state"] == BLOCKED)
		active = [s for s in result["stages"] if s["state"] in (CURRENT, BLOCKED)]
		self.assertEqual(len(active), 1)

	# ------------------------------------------------------------ all completed
	def test_confirmed_contract_is_all_completed(self):
		doc = self.confirm(self.external())
		result = self.timeline(doc)
		self.assertEqual(self.states(result), [COMPLETED] * 6)
		self.assertEqual(result["transaction"]["status"], "Confirmed")
		approval = self.stage(result, "terms_approval")
		self.assertEqual(approval["responsible"], frappe.utils.get_fullname(SALES_MANAGER))
		self.assertEqual(approval["timestamp"], str(doc.terms_approved_on))
		self.assertEqual(approval["record"], {"doctype": "Sidra Sale Contract", "name": doc.name})
		self.assertEqual(
			self.stage(result, "registration_finalized")["timestamp"], str(doc.terms_approved_on)
		)
		for stage in result["stages"]:
			self.assertEqual(stage["allowed_actions"], [], stage["key"])

	def test_confirmed_contract_keeps_its_own_tolerance(self):
		doc = self.confirm(self.external(10000, 9996))
		frappe.db.set_single_value("Sidra Contract Settings", "schedule_tolerance", 1)
		schedule = self.stage(self.timeline(doc), "schedule_validated")
		self.assertEqual(schedule["state"], COMPLETED)
		self.assertEqual(schedule["figures"]["tolerance"], 5)
		self.assertEqual(schedule["figures"]["difference"], 4)

	# ------------------------------------------------------------ stage 1: informational
	def test_buyer_stage_shows_the_verification(self):
		buyer = self.stage(self.timeline(self.external()), "buyer_verified")
		self.assertEqual(buyer["state"], COMPLETED)
		self.assertFalse(buyer["skipped"])
		self.assertEqual(buyer["record"], {"doctype": "Sidra Customer KYC", "name": BUYER})
		self.assertTrue(buyer["timestamp"])

	def test_missing_kyc_never_blocks_a_registered_contract(self):
		result = self.timeline(self.external(customer=self.buyer_without_kyc()))
		buyer = self.stage(result, "buyer_verified")
		self.assertEqual(buyer["state"], COMPLETED)
		self.assertTrue(buyer["skipped"])
		self.assertIn("Not required for registered contracts", buyer["detail"])
		self.assertIsNone(buyer["responsible"])
		self.assertIsNone(buyer["timestamp"])
		self.assertEqual(buyer["allowed_actions"], ["create_kyc"])
		self.assert_stopped_at(result, "terms_approval", CURRENT)

	# ------------------------------------------------------------ stopped at each stage
	def test_stopped_at_property_allocation(self):
		doc = self.external()
		frappe.db.set_value("Sidra Unit", doc.units[0].unit, "status", "Blocked")
		result = self.timeline(doc)
		self.assert_stopped_at(result, "property_allocation", BLOCKED)
		allocation = self.stage(result, "property_allocation")
		self.assertIn(f"Unit {doc.units[0].unit} is Blocked", allocation["blocker"]["reason"])
		self.assertEqual(allocation["blocker"]["action_key"], "edit_contract")
		self.assertIn(
			"After: Property allocation checked", self.stage(result, "agreement_attached")["detail"]
		)

	def test_stopped_at_agreement(self):
		result = self.timeline(self.external(attach=False), SALES_USER)
		self.assert_stopped_at(result, "agreement_attached", CURRENT)
		agreement = self.stage(result, "agreement_attached")
		self.assertEqual(agreement["next_action"], "attach_agreement")
		self.assertEqual(agreement["allowed_actions"], ["attach_agreement"])
		self.assertIsNone(agreement["blocker"])

	def own_file(self, doc):
		return frappe.db.get_value(
			"File",
			{"file_url": doc.signed_copy, "attached_to_name": doc.name, "attached_to_field": "signed_copy"},
		)

	def test_agreement_not_on_the_signed_copy_field_is_blocked(self):
		doc = self.external()
		frappe.db.set_value("File", self.own_file(doc), "attached_to_field", None)
		result = self.timeline(doc)
		self.assert_stopped_at(result, "agreement_attached", BLOCKED)
		agreement = self.stage(result, "agreement_attached")
		self.assertIn("Signed Copy field", agreement["blocker"]["reason"])
		self.assertEqual(agreement["blocker"]["action_key"], "attach_agreement")

	def test_agreement_file_shared_with_another_record_is_blocked(self):
		doc = self.external()
		other = self.external(attach=False)
		# A second File row for the same stored file, attached to another contract.
		shared = frappe.copy_doc(frappe.get_doc("File", self.own_file(doc)))
		shared.attached_to_name = other.name
		shared.name = frappe.generate_hash(length=10)
		shared.db_insert()
		result = self.timeline(doc)
		self.assert_stopped_at(result, "agreement_attached", BLOCKED)
		self.assertIn("another record", self.stage(result, "agreement_attached")["blocker"]["reason"])

	def test_stopped_at_schedule_without_rows(self):
		result = self.timeline(self.external(rows=False))
		self.assert_stopped_at(result, "schedule_validated", CURRENT)
		self.assertEqual(self.stage(result, "schedule_validated")["figures"]["rows"], 0)

	def test_blocked_schedule_gives_reason_and_amounts(self):
		result = self.timeline(self.external(10000, 9000))
		self.assert_stopped_at(result, "schedule_validated", BLOCKED)
		schedule = self.stage(result, "schedule_validated")
		reason = schedule["blocker"]["reason"]
		for amount in ("9,000.00", "10,000.00", "1,000.00", "5.00"):
			self.assertIn(amount, reason)
		self.assertIn("differs from the amount due", reason)
		self.assertEqual(schedule["blocker"]["action_key"], "edit_schedule")
		self.assertEqual(
			{k: schedule["figures"][k] for k in ("schedule_total", "amount_due", "difference", "tolerance")},
			{"schedule_total": 9000, "amount_due": 10000, "difference": 1000, "tolerance": 5},
		)

	def test_difference_within_tolerance_does_not_block(self):
		result = self.timeline(self.external(10000, 9996))
		self.assert_stopped_at(result, "terms_approval", CURRENT)
		self.assertIn("within the limit", self.stage(result, "schedule_validated")["detail"])

	def test_stopped_at_terms_approval_and_actions_follow_the_user(self):
		doc = self.external()
		result = self.timeline(doc, SALES_MANAGER)
		self.assert_stopped_at(result, "terms_approval", CURRENT)
		approval = self.stage(result, "terms_approval")
		self.assertEqual(approval["responsible"], "Sidra Sales Manager")
		self.assertEqual(approval["next_action"], "confirm_contract")
		self.assertEqual(approval["allowed_actions"], ["confirm_contract"])
		for user in (SALES_USER, GENERAL_MANAGER, FINANCE_REVIEWER):
			approval = self.stage(self.timeline(doc, user), "terms_approval")
			self.assertEqual(approval["state"], CURRENT)
			self.assertEqual(approval["allowed_actions"], [], user)

	def test_terms_approval_blocked_by_missing_reference_and_legal_hold(self):
		result = self.timeline(self.external(external_reference=""))
		self.assert_stopped_at(result, "terms_approval", BLOCKED)
		self.assertIn("external reference", self.stage(result, "terms_approval")["blocker"]["reason"])

		held = self.external(contract_profile=make_held_profile().name)
		held.schedule[0].amount = held.amount_due  # the profile pre-fills a separate down payment
		held.save(ignore_permissions=True)
		self.assertEqual(self.stage(self.timeline(held), "schedule_validated")["state"], COMPLETED)
		approval = self.stage(self.timeline(held), "terms_approval")
		self.assertEqual(approval["state"], BLOCKED)
		self.assertIn("legal hold", approval["blocker"]["reason"])
		self.assertNotIn("confirm_contract", approval["allowed_actions"])

	def test_terms_approval_blocked_by_duplicate_reference(self):
		first = self.confirm(self.external())
		second = self.external(external_reference=first.external_reference)
		approval = self.stage(self.timeline(second), "terms_approval")
		self.assertEqual(approval["state"], BLOCKED)
		self.assertIn(first.name, approval["blocker"]["reason"])

	# ------------------------------------------------------------ permissions
	def test_user_without_read_permission_is_refused(self):
		doc = self.external()
		with as_user(OUTSIDER), self.assertRaises(frappe.PermissionError):
			get_contract_timeline(doc.name)
		with as_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_contract_timeline(doc.name)

	def test_unknown_contract_is_not_an_empty_timeline(self):
		with as_user(SALES_MANAGER), self.assertRaises(frappe.DoesNotExistError):
			get_contract_timeline("SSC-0000-NOPE")

	def test_restricted_user_gets_unavailable_for_kyc(self):
		"""G12: only sales staff and the General Manager read KYC. Others are told nothing about it."""
		for customer in (BUYER, self.buyer_without_kyc()):
			doc = self.external(customer=customer)
			for user in (FINANCE_REVIEWER, SYSTEM_ONLY):
				result = self.timeline(doc, user)
				buyer = self.stage(result, "buyer_verified")
				self.assertTrue(buyer["unavailable"], (customer, user))
				self.assertFalse(buyer["skipped"])
				self.assertIn(UNAVAILABLE, buyer["detail"])
				for field in ("responsible", "timestamp", "record"):
					self.assertIsNone(buyer[field], (customer, user, field))
				self.assertEqual(buyer["allowed_actions"], [])
				self.assert_stopped_at(result, "terms_approval", CURRENT)
		# The same contract for a user who may read KYC.
		self.assertFalse(self.stage(self.timeline(doc, GENERAL_MANAGER), "buyer_verified")["unavailable"])

	def test_amounts_are_unavailable_without_field_access(self):
		"""No amount is restricted today; if one ever is, the figure is withheld, never zeroed."""
		doc = self.external(10000, 9000)
		with patch("sidra_realestate.api.workflow._can_see_money", return_value=False):
			schedule = self.stage(self.timeline(doc), "schedule_validated")
		self.assertEqual(schedule["state"], BLOCKED)
		for key in ("schedule_total", "amount_due", "difference"):
			self.assertEqual(schedule["figures"][key], UNAVAILABLE)
		for amount in ("9,000.00", "10,000.00", "1,000.00"):
			self.assertNotIn(amount, schedule["blocker"]["reason"])

	# ------------------------------------------------------------ other contracts
	def test_generated_contract_reports_no_workflow_yet(self):
		doc = make_confirmed_contract("_TEST-WFL")
		result = self.timeline(doc)
		self.assertFalse(result["supported"])
		self.assertEqual(result["stages"], [])
		self.assertIsNone(result["transaction"]["process"])
		self.assertTrue(result["reason"])

	# ------------------------------------------------------------ read-only
	def test_calling_twice_changes_nothing(self):
		draft = self.external(10000, 9000)
		confirmed = self.confirm(self.external())

		def fingerprint():
			rows = frappe.get_all(
				"Sidra Sale Contract",
				filters={"name": ("in", [draft.name, confirmed.name])},
				fields=["name", "modified", "docstatus"],
				order_by="name",
			)
			counts = [
				frappe.db.count(doctype)
				for doctype in ("Sidra Sale Contract", "File", "Version", "Comment", "Sidra Customer KYC")
			]
			units = frappe.get_all(
				"Sidra Unit",
				filters={"name": ("in", [draft.units[0].unit, confirmed.units[0].unit])},
				fields=["name", "modified", "status"],
				order_by="name",
			)
			return rows, counts, units

		before = fingerprint()
		statements = []
		run = frappe.db.sql

		def recording(query, *args, **kwargs):
			statements.append(str(query))
			return run(query, *args, **kwargs)

		with patch.object(frappe.db, "sql", side_effect=recording):
			first = [
				self.timeline(doc, user) for doc in (draft, confirmed) for user in (SALES_MANAGER, SALES_USER)
			]
			second = [
				self.timeline(doc, user) for doc in (draft, confirmed) for user in (SALES_MANAGER, SALES_USER)
			]

		self.assertEqual(first, second)
		self.assertTrue(statements, "the recorder saw the queries")
		self.assertEqual([s for s in statements if WRITE.match(s)], [])
		self.assertEqual(fingerprint(), before)
