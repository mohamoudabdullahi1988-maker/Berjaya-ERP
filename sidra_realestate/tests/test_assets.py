# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""G41: asset categories take Finance's accounts; no depreciation entry before Finance approves."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.services.assets import (
	APPROVED,
	keep_depreciation_off,
	refuse_depreciation_entry,
	setup_asset_categories,
)
from sidra_realestate.tests.helpers import COMPANY, SALES_MANAGER, as_user, ensure_base_records


class TestAssets(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_depreciation_entries_wait_for_finance(self):
		entry = frappe._dict(voucher_type="Depreciation Entry")
		with patch.dict(frappe.conf, {APPROVED: 0}), self.assertRaisesRegex(frappe.ValidationError, "G41"):
			refuse_depreciation_entry(entry)
		with patch.dict(frappe.conf, {APPROVED: 1}):
			refuse_depreciation_entry(entry)
		with patch.dict(frappe.conf, {APPROVED: 0}):
			refuse_depreciation_entry(frappe._dict(voucher_type="Journal Entry"))

	def test_automatic_depreciation_kept_off(self):
		frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)
		with patch.dict(frappe.conf, {APPROVED: 0}):
			keep_depreciation_off()
		self.assertFalse(
			frappe.db.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically")
		)

	def test_categories_need_finance_accounts_of_the_right_type(self):
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			setup_asset_categories(COMPANY, "x", "y", "z")
		any_ledger = frappe.db.get_value("Account", {"company": COMPANY, "is_group": 0}, "name")
		with as_user("Administrator"), self.assertRaises(frappe.ValidationError):
			setup_asset_categories(COMPANY, any_ledger, any_ledger, any_ledger)
