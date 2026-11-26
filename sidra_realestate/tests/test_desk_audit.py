"""The Desk data audit count is read only and for System Managers."""

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.desk_audit import MODULES, count_records
from sidra_realestate.tests.helpers import COMPANY, SALES_MANAGER, as_user, ensure_base_records


class TestDeskAudit(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_counts_every_module_and_changes_nothing(self):
		before = frappe.db.count("Version")
		with as_user("Administrator"):
			result = count_records(company=COMPANY)
		self.assertEqual(set(result), set(MODULES))
		self.assertEqual(result["Projects"]["Project"], frappe.db.count("Project", {"company": COMPANY}))
		self.assertEqual(frappe.db.count("Version"), before)

	def test_only_system_managers(self):
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			count_records()

	def test_role_visibility_reads_actual_rights(self):
		from sidra_realestate.desk_audit import VISIBILITY, role_visibility
		from sidra_realestate.tests.helpers import PROJECT_MANAGER, SALES_USER

		with as_user("Administrator"):
			result = role_visibility(users=[SALES_USER, PROJECT_MANAGER])
		self.assertEqual(set(result), {SALES_USER, PROJECT_MANAGER})
		self.assertEqual(set(result[SALES_USER]), set(VISIBILITY))
		self.assertIn("read", result[PROJECT_MANAGER]["Project"])  # Projects User
		self.assertNotIn("read", result[SALES_USER]["Task"])
		with as_user(SALES_MANAGER), self.assertRaises(frappe.PermissionError):
			role_visibility()
