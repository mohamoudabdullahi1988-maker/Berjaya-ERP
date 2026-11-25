"""Security posture audit must remain administrative, read-only and free of secret values."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sidra_realestate.security import audit_site
from sidra_realestate.tests.helpers import OUTSIDER, as_user, ensure_base_records


class TestSecurityAudit(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_base_records()

	def test_unauthorized_user_cannot_inspect_settings(self):
		with as_user(OUTSIDER), patch("sidra_realestate.security.frappe.get_single") as read:
			with self.assertRaises(frappe.PermissionError):
				audit_site()
			read.assert_not_called()

	def test_reports_risks_without_leaking_configuration(self):
		config = frappe._dict(
			ignore_csrf=1,
			allow_cors=["*"],
			host_name="http://test.invalid",
			allow_tests=1,
			rate_limit={"limit": 0, "window": 3600},
			db_password="SENTINEL-NOT-A-REAL-CREDENTIAL",  # pragma: allowlist secret -- synthetic leak sentinel
		)
		with patch("sidra_realestate.security.frappe.conf", config):
			with patch("sidra_realestate.security.frappe.db.set_value") as write:
				result = audit_site()
				write.assert_not_called()
		checks = {row["control"]: row["status"] for row in result["checks"]}
		self.assertEqual(checks["ignore_csrf_disabled"], "fail")
		self.assertEqual(checks["allow_tests_disabled"], "fail")
		self.assertEqual(checks["cors"], "fail")
		self.assertEqual(checks["declared_https_origin"], "review")
		self.assertEqual(checks["frappe_request_time_budget"], "review")
		self.assertNotIn(config.db_password, frappe.as_json(result))
		self.assertNotIn("db_password", frappe.as_json(result))
