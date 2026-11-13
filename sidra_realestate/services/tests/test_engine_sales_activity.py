import unittest

from sidra_realestate.services.sales_activity import lead_status_summary


class TestLeadStatusSummary(unittest.TestCase):
	def test_recorded_status_is_not_a_conversion_claim(self):
		data = lead_status_summary(
			[{"status": "Lead"}, {"status": "Lead"}, {"status": "Converted"}, {"status": None}]
		)
		self.assertEqual(
			data["pipeline"],
			[
				{"label": "Converted", "value": 1},
				{"label": "Lead", "value": 2},
				{"label": "Unspecified", "value": 1},
			],
		)
		self.assertIsNone(data["conversion_rate"])
		self.assertIsNone(data["qualified_opportunities"])

	def test_empty_readable_cohort_is_available(self):
		self.assertEqual(lead_status_summary([])["pipeline"], [])
		self.assertTrue(lead_status_summary([])["available"])
