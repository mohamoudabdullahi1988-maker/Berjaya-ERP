"""Pure tests for the field-rule parser used by the Berjaya forms. No Frappe needed."""

import json
import unittest
from pathlib import Path

from sidra_realestate.services.form_rules import evaluate, parse

APP = Path(__file__).resolve().parents[2]
RULE_KEYS = ("depends_on", "read_only_depends_on", "mandatory_depends_on")


class TestFormRules(unittest.TestCase):
	def test_every_rule_in_the_app_is_understood(self):
		"""A rule the parser cannot read would be shown/editable by default; none may exist."""
		seen = 0
		for path in APP.glob("sidra_*/doctype/*/*.json"):
			meta = json.loads(path.read_text())
			if meta.get("doctype") != "DocType":
				continue
			for field in meta.get("fields", []):
				for key in RULE_KEYS:
					if field.get(key):
						seen += 1
						with self.subTest(doctype=meta["name"], field=field["fieldname"], rule=field[key]):
							self.assertIsNotNone(parse(field[key]))
		self.assertGreater(seen, 50)

	def test_comparisons_and_logic(self):
		rule = parse("eval:doc.contract_type=='Installment' && doc.source=='External (registered)'")
		self.assertTrue(evaluate(rule, {"contract_type": "Installment", "source": "External (registered)"}))
		self.assertFalse(evaluate(rule, {"contract_type": "Installment", "source": "Generated from profile"}))
		rule = parse(
			"eval:doc.source!='External (registered)' || doc.down_payment_mode!='Recorded separately'"
		)
		self.assertFalse(
			evaluate(rule, {"source": "External (registered)", "down_payment_mode": "Recorded separately"})
		)
		self.assertTrue(evaluate(rule, {"source": "External (registered)", "down_payment_mode": "None"}))
		self.assertTrue(
			evaluate(parse('eval:doc.pricing_basis=="Fixed Fee"'), {"pricing_basis": "Fixed Fee"})
		)

	def test_negation_and_truthiness(self):
		self.assertTrue(evaluate(parse("eval:!!doc.current_contract"), {"current_contract": "SSC-1"}))
		self.assertFalse(evaluate(parse("eval:!!doc.current_contract"), {"current_contract": None}))
		self.assertTrue(evaluate(parse("eval:!doc.__islocal"), {}))
		self.assertFalse(evaluate(parse("eval:!doc.__islocal"), {"__islocal": 1}))
		self.assertFalse(evaluate(parse("title_refund_after_days"), {"title_refund_after_days": 0}))
		self.assertTrue(evaluate(parse("title_refund_after_days"), {"title_refund_after_days": 30}))
		self.assertTrue(evaluate(parse("legal_hold"), {"legal_hold": 1}))

	def test_lists(self):
		rule = parse("eval:['House','Apartment'].includes(doc.unit_type)")
		self.assertEqual(rule, {"in": [["House", "Apartment"], {"field": "unit_type"}]})
		self.assertTrue(evaluate(rule, {"unit_type": "House"}))
		self.assertFalse(evaluate(rule, {"unit_type": "Plot"}))
		rule = parse("eval:in_list(['Fixed','Percent'], doc.refund_retention_type)")
		self.assertTrue(evaluate(rule, {"refund_retention_type": "Percent"}))

	def test_blank_compares_as_empty_text(self):
		rule = parse("eval:doc.title_penalty_type!='None'")
		self.assertTrue(evaluate(rule, {"title_penalty_type": None}))
		self.assertFalse(evaluate(rule, {"title_penalty_type": "None"}))

	def test_anything_else_is_not_understood(self):
		for rule in (
			"eval:doc.a > 1",
			"eval:frappe.user.has_role('X')",
			"eval:doc.a.length",
			"eval:(doc.a == 'x'",
			"eval:doc.a == 'x'; alert(1)",
			"eval:",
			"two words",
			"",
			None,
		):
			with self.subTest(rule=rule):
				self.assertIsNone(parse(rule))

	def test_tree_is_plain_json(self):
		rule = parse("eval:doc.a=='x' && (doc.b!='y' || !doc.c)")
		self.assertEqual(json.loads(json.dumps(rule)), rule)


if __name__ == "__main__":
	unittest.main()
