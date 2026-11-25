"""Fictional company assets (G40) on the disposable CI site.

Run by `test_demo_datasets.TestDemo7Assets`, after the pilot dataset is loaded.
"""

from unittest.mock import patch

import frappe

from sidra_realestate.finance_demo import COMPANY, FLAGS
from sidra_realestate.pilot_assets import ASSETS, create_pilot_assets
from sidra_realestate.services.assets import CATEGORIES
from sidra_realestate.tests.helpers import as_user


class PilotAssetsChecks:
	def test_assets_are_added_once_and_post_nothing(self):
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 0 for flag in FLAGS}):
			with self.assertRaisesRegex(frappe.ValidationError, "staging-only flags"):
				create_pilot_assets()
		with patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}), as_user("sidra.manager@example.com"):
			with self.assertRaises(frappe.PermissionError):
				create_pilot_assets()

		gl_before = frappe.db.count("GL Entry")
		with as_user("Administrator"), patch.dict(frappe.conf, {flag: 1 for flag in FLAGS}):
			data = create_pilot_assets()
			self.assertTrue(data["created"])
			self.assertEqual(len(data["assets"]), len(ASSETS))
			for name in data["assets"]:
				asset = frappe.get_doc("Asset", name)
				self.assertEqual((asset.company, asset.docstatus), (COMPANY, 1))
				book = asset.finance_books[0]
				self.assertEqual(book.depreciation_method, "Straight Line")
				self.assertEqual(book.total_number_of_depreciations, CATEGORIES[asset.asset_category])
			again = create_pilot_assets()
			self.assertFalse(again["created"])
			self.assertEqual(frappe.db.count("Asset", {"company": COMPANY}), len(ASSETS))
		self.assertEqual(frappe.db.count("GL Entry"), gl_before)
