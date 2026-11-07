"""Reporting regression tests against synthetic records and the repository's actual schema."""

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("workbook", ROOT / "integrations/insights/build_workbook.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        # Building tables from the checked-out DocType fields catches referenced
        # field/table drift, without pretending to be a Frappe/MariaDB runtime test.
        for path in (ROOT / "sidra_realestate").glob("**/doctype/*/*.json"):
            schema = json.loads(path.read_text())
            columns = {"name": "TEXT PRIMARY KEY", "docstatus": "INTEGER DEFAULT 0",
                       "parent": "TEXT", "parenttype": "TEXT", "parentfield": "TEXT"}
            for field in schema["fields"]:
                if field["fieldtype"] in ("Section Break", "Column Break", "Tab Break", "HTML", "Table"):
                    continue
                columns[field["fieldname"]] = (
                    "NUMERIC" if field["fieldtype"] in ("Currency", "Float", "Int", "Percent", "Check")
                    else "TEXT")
            ddl = ", ".join(f'`{name}` {kind}' for name, kind in columns.items())
            self.db.execute(f'CREATE TABLE `tab{schema["name"]}` ({ddl})')
        self.db.execute("CREATE TABLE tabCompany (name TEXT PRIMARY KEY, default_currency TEXT)")
        self.insert("Company", name="Example Homes", default_currency="USD")
        self.insert("Company", name="Other Company", default_currency="USD")
        for name in ("A", "B", "TEST"):
            self.insert("Sidra Scheme", name=name, scheme_name="Shared display name",
                        company="Example Homes")
        self.insert("Sidra Scheme", name="OTHER", company="Other Company")
        for name, scheme, company in (("A1", "A", "Example Homes"), ("B1", "B", "Example Homes"),
                                      ("T1", "TEST", "Example Homes"),
                                      ("O1", "OTHER", "Other Company")):
            self.insert("Sidra Unit", name=name, scheme=scheme, company=company,
                        status="Available", unit_type="Plot")
        self.queries = MODULE.build_queries("Example Homes", "USD", "2026-11-01", "2026-11-07", ["TEST"])

    def tearDown(self):
        self.db.close()

    def insert(self, doctype, **values):
        columns = ", ".join(f"`{key}`" for key in values)
        placeholders = ", ".join("?" for _ in values)
        self.db.execute(f"INSERT INTO `tab{doctype}` ({columns}) VALUES ({placeholders})", list(values.values()))

    def contract(self, name="C1", units=(("A1", 600), ("B1", 400)), **changes):
        values = dict(name=name, company="Example Homes", currency="USD", signed_on="2026-11-07",
                      docstatus=1, agreed_price=1000, contract_type="Installment")
        values.update(changes)
        self.insert("Sidra Sale Contract", **values)
        for index, (unit, amount) in enumerate(units):
            self.insert("Sidra Contract Unit", name=f"{name}-U{index}", unit=unit,
                        allocated_price=amount, parent=name, parenttype="Sidra Sale Contract", parentfield="units")

    def schedule(self, name, due_date, amount=100, **changes):
        values = dict(name=name, parent="C1", parenttype="Sidra Sale Contract", parentfield="schedule",
                      row_type="Installment", due_date=due_date, amount=amount)
        values.update(changes)
        self.insert("Sidra Installment Line", **values)

    def rows(self, key):
        return [dict(row) for row in self.db.execute(self.queries[key])]

    def test_all_queries_execute_against_current_schema(self):
        for key in self.queries:
            with self.subTest(query=key):
                self.assertEqual(self.rows(key), []) if key != "inventory" else self.assertEqual(len(self.rows(key)), 2)

    def test_contract_value_is_not_multiplied_by_unit_or_schedule_rows(self):
        self.contract()
        self.schedule("L1", "2026-11-08")
        self.schedule("L2", "2026-11-08", 250, row_type="Fee")
        self.assertEqual(sum(r["signed_sales_value"] for r in self.rows("sales")), 1000)
        self.assertEqual(sum(r["allocated_sales_value"] for r in self.rows("sales_by_scheme")), 1000)
        self.assertEqual(sum(r["scheduled_amount"] for r in self.rows("scheduled_dues")), 350)
        self.assertEqual({r["scheme"] for r in self.rows("sales_by_scheme")}, {"A", "B"})

    def test_sales_excludes_drafts_cancelled_wrong_currency_and_outside_period(self):
        self.contract()
        for name, changes in (("draft", {"docstatus": 0}), ("cancel", {"docstatus": 2}),
                              ("foreign", {"currency": "EUR"}),
                              ("future", {"signed_on": "2026-11-08"}),
                              ("old", {"signed_on": "2026-10-31"}),
                              ("other", {"company": "Other Company"})):
            self.contract(name=name, **changes)
        self.assertEqual([r["contract"] for r in self.rows("sales")], ["C1"])

    def test_mixed_company_missing_units_and_excluded_scheme_fail_closed(self):
        for name, unit in (("mixed", "O1"), ("missing", "MISSING"), ("test", "T1")):
            self.contract(name=name, units=(("A1", 600), (unit, 400)))
        self.contract(name="empty", units=())
        for key in ("sales", "sales_by_scheme", "scheduled_dues"):
            self.assertEqual(self.rows(key), [])

    def test_upcoming_window_includes_tomorrow_and_day_30_only(self):
        self.contract(signed_on="2026-10-01")  # Older contracts still have upcoming obligations.
        for name, due in (("past", "2026-11-06"), ("today", "2026-11-07"),
                          ("first", "2026-11-08"), ("last", "2026-12-07"), ("later", "2026-12-08")):
            self.schedule(name, due)
        self.assertEqual({r["schedule_row"] for r in self.rows("scheduled_dues")}, {"first", "last"})

    def test_wrong_child_parentfield_and_parenttype_are_ignored(self):
        self.contract()
        self.schedule("wrong-field", "2026-11-09", parentfield="other")
        self.schedule("wrong-type", "2026-11-09", parenttype="Other DocType")
        self.assertEqual(self.rows("scheduled_dues"), [])

    def test_inventory_is_current_and_company_scoped(self):
        self.db.execute("UPDATE `tabSidra Unit` SET status = 'Under Contract' WHERE name = 'A1'")
        rows = self.rows("inventory")
        self.assertEqual({r["unit"] for r in rows}, {"A1", "B1"})
        self.assertEqual(sum(r["available_count"] for r in rows), 1)
        self.assertEqual(sum(r["unit_count"] for r in rows), 2)

    def test_stage_date_exceptions_are_not_an_invented_progress_score(self):
        self.insert("Sidra Construction Job", name="J1", company="Example Homes", currency="USD", status="In Progress")
        for name, planned, actual, progress in (("late-open", "2026-11-06", None, 50),
                                               ("late-finish", "2026-11-05", "2026-11-06", 100),
                                               ("today", "2026-11-07", None, 20),
                                               ("unknown", None, None, None),
                                               ("on-time", "2026-11-05", "2026-11-05", 100)):
            self.insert("Sidra Project Stage", name=name, parent="J1", parenttype="Sidra Construction Job",
                        parentfield="stages", planned_end=planned, actual_end=actual, completion_pct=progress)
        flagged = {r["stage"] for r in self.rows("construction_stages") if r["stage_date_exception"]}
        self.assertEqual(flagged, {"late-open", "late-finish"})

    def test_no_receipt_or_ledger_is_invented(self):
        workbook = MODULE.build_workbook("Example Homes", "USD", "2026-11-01", "2026-11-07")
        text = " ".join(i.get("text", "") for i in workbook["dependencies"]["dashboards"]["sidra-overview"]["items"])
        self.assertIn("Unavailable:", text)
        self.assertIn("not expected receipts", text)
        self.assertNotIn("paid_amount", " ".join(self.queries.values()))

    def test_export_references_are_complete_and_private(self):
        w = MODULE.build_workbook("Example Homes", "USD", "2026-11-01", "2026-11-07")
        deps = w["dependencies"]
        self.assertEqual(w["type"], "Workbook")
        for chart in deps["charts"].values():
            self.assertIn(chart["query"], deps["queries"])
            self.assertEqual(chart["is_public"], 0)
        dashboard = deps["dashboards"]["sidra-overview"]
        self.assertEqual(dashboard["is_public"], 0)
        for item in dashboard["items"]:
            if item["type"] == "chart":
                self.assertIn(item["chart"], deps["charts"])

    def test_scope_literals_and_dates_are_validated(self):
        self.assertEqual(MODULE.literal("Owner's Homes"), "'Owner''s Homes'")
        for value in ("", " ", "a\\b", "a\x00b", "a\nb"):
            with self.assertRaises(ValueError):
                MODULE.literal(value)
        for start, end in (("2026-11-08", "2026-11-07"), ("2026-02-30", "2026-11-07")):
            with self.assertRaises(ValueError):
                MODULE.build_queries("Example Homes", "USD", start, end)

    def test_quote_in_company_name_remains_a_literal(self):
        self.contract()
        queries = MODULE.build_queries("Example Homes' OR 1=1 --", "USD", "2026-11-01", "2026-11-07")
        for query in queries.values():
            self.assertEqual(self.db.execute(query).fetchall(), [])


if __name__ == "__main__":
    unittest.main()
