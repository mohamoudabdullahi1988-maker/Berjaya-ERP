"""Native import/query smoke test. Refuses any site except the disposable CI site."""

import importlib.util
import json
import os
from decimal import Decimal
from pathlib import Path


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run():
    import frappe
    import frappe.share
    from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook

    if os.environ.get("SIDRA_INSIGHTS_DISPOSABLE_SITE") != "1" or frappe.local.site != "insights_ci":
        raise RuntimeError("This test only runs on disposable insights_ci with SIDRA_INSIGHTS_DISPOSABLE_SITE=1")
    check(frappe.session.user == "Administrator", "Run as Administrator on the disposable site")
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("sidra_insights_builder", root / "integrations/insights/build_workbook.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    def insert(doctype, **values):
        # Synthetic reporting fixtures intentionally bypass sales validation. This
        # tests import/query execution, not legal confirmation or accounting logic.
        frappe.get_doc({"doctype": doctype, **values}).db_insert()

    company, other = "Insights CI Homes", "Insights CI Other"
    for name in (company, other):
        insert("Company", name=name, company_name=name, default_currency="USD")
    insert("Customer", name="INSIGHTS-CI-BUYER", customer_name="Synthetic Buyer", customer_type="Individual")
    for name, owner in (("INSIGHTS-CI-A", company), ("INSIGHTS-CI-B", company), ("INSIGHTS-CI-OTHER", other)):
        insert("Sidra Scheme", name=name, scheme_code=name, scheme_name=name, company=owner)
    for name, scheme, owner, status in (
        ("INSIGHTS-CI-A1", "INSIGHTS-CI-A", company, "Under Contract"),
        ("INSIGHTS-CI-B1", "INSIGHTS-CI-B", company, "Under Contract"),
        ("INSIGHTS-CI-A2", "INSIGHTS-CI-A", company, "Available"),
        ("INSIGHTS-CI-O1", "INSIGHTS-CI-OTHER", other, "Available"),
    ):
        insert("Sidra Unit", name=name, unit_code=name, scheme=scheme, company=owner,
               unit_type="Plot", status=status)
    insert("Sidra Sale Contract", name="INSIGHTS-CI-C1", docstatus=1, company=company,
           currency="USD", customer="INSIGHTS-CI-BUYER", agreed_price=1000,
           signed_on="2026-11-07", contract_type="Installment", source="External (registered)")
    for index, (unit, value) in enumerate((("INSIGHTS-CI-A1", 600), ("INSIGHTS-CI-B1", 400))):
        insert("Sidra Contract Unit", name=f"INSIGHTS-CI-CU-{index}", parent="INSIGHTS-CI-C1",
               parenttype="Sidra Sale Contract", parentfield="units", unit=unit, allocated_price=value)
    for index, (due, value, kind) in enumerate((
        ("2026-11-07", 999, "Installment"), ("2026-11-08", 100, "Installment"),
        ("2026-11-08", 50, "Fee"), ("2026-12-07", 250, "Installment"),
        ("2026-12-08", 888, "Installment"),
    )):
        insert("Sidra Installment Line", name=f"INSIGHTS-CI-L-{index}", parent="INSIGHTS-CI-C1",
               parenttype="Sidra Sale Contract", parentfield="schedule", seq=index + 1,
               due_date=due, amount=value, row_type=kind)
    insert("Sidra Construction Job", name="INSIGHTS-CI-J1", company=company, currency="USD",
           customer="INSIGHTS-CI-BUYER", status="In Progress", service_type="Full Construction")
    insert("Sidra Project Stage", name="INSIGHTS-CI-ST1", parent="INSIGHTS-CI-J1",
           parenttype="Sidra Construction Job", parentfield="stages", stage_name="Synthetic milestone",
           planned_end="2026-11-06", completion_pct=25, status="In Progress")
    # Insights uses its own read connection, which must see committed fixtures.
    frappe.db.commit()

    source = frappe.get_doc("Insights Data Source v3", "Site DB")
    source.update_table_list()
    frappe.db.commit()
    payload = builder.build_workbook(company, "USD", "2026-11-01", "2026-11-07")
    workbook = import_workbook(payload)
    frappe.db.commit()
    charts = frappe.get_all("Insights Chart v3", filters={"workbook": workbook}, fields=["name", "query", "is_public"])
    dashboards = frappe.get_all("Insights Dashboard v3", filters={"workbook": workbook}, fields=["name", "is_public", "items"])
    check(len(charts) == 8 and len(dashboards) == 1, "Expected eight charts and one dashboard")
    check(not any(c.is_public for c in charts) and not dashboards[0].is_public, "Imported objects must remain private")
    check(len([i for i in json.loads(dashboards[0].items) if i["type"] == "chart"]) == 8,
          "Dashboard must retain all imported chart references")

    source_query_ids = {chart.query for chart in charts}
    # The five source queries are distinct from the chart data_query stubs which
    # Insights populates when its UI opens a chart. Test actual MariaDB/Ibis here.
    results = {}
    for name in source_query_ids:
        doc = frappe.get_doc("Insights Query v3", name)
        results[doc.title] = doc.execute(force=True, page_size=500)["rows"]
    expected = {"Sales": 1, "Sales By Scheme": 2, "Inventory": 3,
                "Scheduled Dues": 3, "Construction Stages": 1}
    check({title: len(rows) for title, rows in results.items()} == expected, "Native query row counts do not reconcile")

    def total(title, field):
        return sum((Decimal(str(row[field])) for row in results[title]), Decimal(0))

    check(total("Sales", "signed_sales_value") == 1000, "Parent sales total multiplied or lost")
    check(total("Sales By Scheme", "allocated_sales_value") == 1000, "Scheme allocations do not reconcile")
    check(total("Scheduled Dues", "scheduled_amount") == 400, "Upcoming window/same-day rows do not reconcile")
    check(total("Inventory", "available_count") == 1, "Other-company inventory leaked")
    check(total("Construction Stages", "stage_date_exception") == 1, "Stage date exception missing")

    # Verify document sharing boundaries independently of administrator execution.
    viewer, outsider = "insights.viewer@example.invalid", "insights.outsider@example.invalid"
    for email in (viewer, outsider):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Synthetic Insights User",
                        "enabled": 1, "send_welcome_email": 0,
                        "roles": [{"role": "Insights User"}]}).insert()
    frappe.share.add("Insights Workbook", workbook, user=viewer, read=1, write=0, share=0)
    frappe.db.commit()
    objects = [("Insights Workbook", workbook), ("Insights Dashboard v3", dashboards[0].name)]
    objects += [("Insights Chart v3", chart.name) for chart in charts]
    objects += [("Insights Query v3", name) for name in source_query_ids]
    for doctype, name in objects:
        doc = frappe.get_doc(doctype, name)
        check(frappe.has_permission(doctype, "read", doc, user=viewer), f"Read-only viewer cannot read {doctype}")
        check(not frappe.has_permission(doctype, "write", doc, user=viewer), f"Viewer can edit {doctype}")
        for user in (outsider, "Guest"):
            check(not frappe.has_permission(doctype, "read", doc, user=user), f"Private {doctype} readable by unrelated user")

    print(json.dumps({"status": "passed", "workbook": workbook, "queries": 5, "charts": 8,
                      "dashboard": 1, "native_row_counts": expected,
                      "document_access_checks": len(objects) * 4,
                      "limitations": "No browser rendering, HTTP/export authorization or production data-source permissions tested"}))


if __name__ == "__main__":
    run()
