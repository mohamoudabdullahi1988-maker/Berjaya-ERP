"""Build a private Insights v3 workbook export; never connects to Sidra or writes ERP data."""

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def literal(value):
    # Backslashes/control characters are rejected so SQL modes cannot change escaping.
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or c == "\\" for c in value):
        raise ValueError("Scope values must be nonempty text without backslashes/control characters")
    return "'" + value.replace("'", "''") + "'"


def build_queries(company, currency, period_start, as_of, excluded_schemes=()):
    start, end = date.fromisoformat(period_start), date.fromisoformat(as_of)
    if start > end:
        raise ValueError("period_start must not follow as_of")
    company_sql, currency_sql = literal(company), literal(currency)
    excluded = ", ".join(literal(s) for s in excluded_schemes)
    exclude_unit = f"AND u.scheme NOT IN ({excluded})" if excluded else ""
    exclude_bad = f"OR u.scheme IN ({excluded})" if excluded else ""
    # Exclude the entire contract if any unit has an inconsistent/missing company or
    # belongs to an excluded scheme. Never silently report a partial contract value.
    eligible = f"""c.docstatus = 1 AND c.company = {company_sql}
      AND c.currency = {currency_sql} AND c.signed_on <= '{end}'
      AND EXISTS (SELECT 1 FROM `tabSidra Contract Unit` cu
          WHERE cu.parent = c.name AND cu.parenttype = 'Sidra Sale Contract'
          AND cu.parentfield = 'units')
      AND NOT EXISTS (
          SELECT 1 FROM `tabSidra Contract Unit` cu
          LEFT JOIN `tabSidra Unit` u ON u.name = cu.unit
          LEFT JOIN `tabSidra Scheme` s ON s.name = u.scheme
          WHERE cu.parent = c.name AND cu.parenttype = 'Sidra Sale Contract'
          AND cu.parentfield = 'units'
          AND (u.name IS NULL OR s.name IS NULL OR u.company IS NULL
               OR u.company <> c.company OR s.company IS NULL
               OR s.company <> c.company {exclude_bad}))"""
    return {
        "sales": f"""SELECT c.name AS contract, c.signed_on, c.contract_type, c.source,
          c.company, c.currency, c.agreed_price AS signed_sales_value
          FROM `tabSidra Sale Contract` c WHERE {eligible}
          AND c.signed_on >= '{start}'""",
        "sales_by_scheme": f"""SELECT c.name AS contract, s.name AS scheme,
          s.scheme_name, u.name AS unit, c.signed_on, c.currency,
          cu.allocated_price AS allocated_sales_value
          FROM `tabSidra Sale Contract` c
          JOIN `tabSidra Contract Unit` cu ON cu.parent = c.name
            AND cu.parenttype = 'Sidra Sale Contract' AND cu.parentfield = 'units'
          JOIN `tabSidra Unit` u ON u.name = cu.unit
          JOIN `tabSidra Scheme` s ON s.name = u.scheme
          WHERE {eligible} AND c.signed_on >= '{start}'""",
        "inventory": f"""SELECT u.name AS unit, s.name AS scheme, s.scheme_name,
          u.unit_type, u.status, u.offplan_status, u.delivery_date,
          u.company, {currency_sql} AS currency, 1 AS unit_count,
          CASE WHEN u.status = 'Available' THEN 1 ELSE 0 END AS available_count
          FROM `tabSidra Unit` u JOIN `tabSidra Scheme` s ON s.name = u.scheme
          JOIN `tabCompany` co ON co.name = u.company
          WHERE u.company = {company_sql} AND s.company = u.company
          AND co.default_currency = {currency_sql} {exclude_unit}""",
        "scheduled_dues": f"""SELECT c.name AS contract, l.name AS schedule_row,
          l.seq, l.row_type, l.due_date, l.amount AS scheduled_amount,
          c.company, c.currency
          FROM `tabSidra Sale Contract` c
          JOIN `tabSidra Installment Line` l ON l.parent = c.name
            AND l.parenttype = 'Sidra Sale Contract' AND l.parentfield = 'schedule'
          WHERE {eligible} AND c.contract_type = 'Installment'
          AND l.due_date >= '{end + timedelta(days=1)}'
          AND l.due_date <= '{end + timedelta(days=30)}'""",
        "construction_stages": f"""SELECT j.name AS job, j.project, j.service_type,
          j.status AS job_status, st.name AS stage, st.stage_name,
          st.planned_end, st.actual_end, st.completion_pct,
          j.company, j.currency,
          CASE WHEN st.planned_end IS NOT NULL AND st.planned_end <> ''
            AND ((st.actual_end IS NOT NULL AND st.actual_end <> ''
                  AND st.actual_end > st.planned_end)
              OR ((st.actual_end IS NULL OR st.actual_end = '')
                  AND st.planned_end < '{end}'
                  AND (st.completion_pct IS NULL OR st.completion_pct < 100)))
            THEN 1 ELSE 0 END AS stage_date_exception
          FROM `tabSidra Construction Job` j
          JOIN `tabSidra Project Stage` st ON st.parent = j.name
            AND st.parenttype = 'Sidra Construction Job' AND st.parentfield = 'stages'
          WHERE j.company = {company_sql} AND j.currency = {currency_sql}
            AND j.status IN ('Contracted', 'In Progress', 'On Hold')""",
    }


def dimension(column, kind="String"):
    return {"column_name": column, "data_type": kind, "dimension_name": column}


def measure(column, label, kind="Decimal"):
    return {"column_name": column, "data_type": kind, "aggregation": "sum", "measure_name": label}


def build_workbook(company, currency, period_start, as_of, data_source="Site DB", excluded_schemes=()):
    literal(data_source)
    sql = build_queries(company, currency, period_start, as_of, excluded_schemes)
    workbook_id = "sidra-ceo-starter-v01"
    queries = {
        key: {"name": key, "title": key.replace("_", " ").title(), "workbook": workbook_id,
              "use_live_connection": 1, "is_native_query": 1, "is_builder_query": 0,
              "is_script_query": 0, "sort_order": index,
              "operations": [{"type": "sql", "data_source": data_source, "raw_sql": query}]}
        for index, (key, query) in enumerate(sql.items())
    }
    charts, items = {}, []

    def text(text, y, height=3):
        items.append({"type": "text", "text": text,
                      "layout": {"i": f"text-{y}", "x": 0, "y": y, "w": 20, "h": height}})

    def chart(key, title, query, chart_type, config, x, y, w, h):
        charts[key] = {"name": key, "title": title, "query": query, "workbook": workbook_id,
                       "chart_type": chart_type, "is_public": 0,
                       "config": {"filters": {"filters": [], "logical_operator": "And"},
                                  "order_by": [], "limit": 1000, **config}}
        items.append({"type": "chart", "chart": key,
                      "layout": {"i": key, "x": x, "y": y, "w": w, "h": h}})

    def number(key, title, query, value, x, width, decimal=0):
        chart(key, title, query, "Number", {
            "number_columns": [value], "number_column_options": [],
            "comparison": False, "sparkline": False, "shorten_numbers": False,
            "decimal": decimal}, x, 4, width, 3)

    # Dashboard text is plain, trusted markup; scope values are escaped separately.
    from html import escape
    text(f"<h2>Sidra Owner Overview — {escape(company)}</h2>"
         f"<p>{escape(currency)} · Signed sales: {period_start}–{as_of}. "
         "Inventory and stages: current records at query refresh. "
         "Date cutoffs are fixed; this is not a historical accounting snapshot.</p>", 0, 4)
    number("sales_total", f"Signed sales value ({currency})", "sales",
           measure("signed_sales_value", "Signed sales value"), 0, 7, 2)
    number("available_units", "Available units now", "inventory",
           measure("available_count", "Available units", "Integer"), 7, 6)
    number("scheduled_total", f"Gross scheduled dues next 30 days ({currency})", "scheduled_dues",
           measure("scheduled_amount", "Gross scheduled dues"), 13, 7, 2)
    text("<p><strong>Unavailable:</strong> cash collected, unpaid overdue balance, cash balance, "
         "forecast margin and collections targets. Receipt/allocation and approved Finance sources "
         "are not integrated. Scheduled dues are obligations before settlements, not expected receipts. "
         "Separately recorded down payments without due dates are outside this schedule.</p>", 7, 4)
    chart("scheme_sales", f"Signed sales by scheme ({currency})", "sales_by_scheme", "Bar", {
        "x_axis": {"dimension": dimension("scheme")},
        "y_axis": {"series": [{"measure": measure("allocated_sales_value", "Allocated sales")}]}},
        0, 11, 10, 7)
    chart("unit_status", "Current inventory by status", "inventory", "Donut", {
        "label_column": dimension("status"),
        "value_column": measure("unit_count", "Units", "Integer")}, 10, 11, 10, 7)
    chart("scheme_inventory", "Inventory by scheme and status", "inventory", "Table", {
        "rows": [dimension("scheme"), dimension("scheme_name"), dimension("status")], "columns": [],
        "values": [measure("unit_count", "Units", "Integer")]}, 0, 18, 20, 7)
    chart("due_rows", "Upcoming contractual schedule — before settlements", "scheduled_dues", "Table", {
        "rows": [dimension("contract"), dimension("schedule_row"), dimension("row_type"),
                 dimension("due_date", "Date")], "columns": [],
        "values": [measure("scheduled_amount", "Scheduled amount")]}, 0, 25, 20, 8)
    chart("stage_rows", "Current construction stage date exceptions", "construction_stages", "Table", {
        "filters": {"logical_operator": "And", "filters": [
            {"column": {"column_name": "stage_date_exception", "type": "column"},
             "operator": "=", "value": 1}]},
        "rows": [dimension("job"), dimension("stage"), dimension("stage_name"),
                 dimension("planned_end", "Date"), dimension("actual_end", "Date")],
        "columns": [], "values": [measure("stage_date_exception", "Exceptions", "Integer")]},
        0, 33, 20, 8)
    text("<p>Source queries retain record IDs for reconciliation. No automatic approvals or financial "
         "actions. Scheme labels are display names; reconcile by scheme ID. Charts have a 1,000-row/group "
         "limit; inspect full queries before relying on totals. Missing results are not proof of zero. "
         "Construction exceptions compare recorded dates; they do not certify an approved baseline.</p>", 41, 4)
    return {"version": "1.0", "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "Workbook", "name": workbook_id,
            "doc": {"name": workbook_id, "title": f"Sidra Owner Overview — {company} — {as_of}"},
            "dependencies": {"folders": [], "queries": queries, "charts": charts,
                             "dashboards": {"sidra-overview": {
                                 "name": "sidra-overview", "title": "Sidra Owner Overview",
                                 "workbook": workbook_id, "is_public": 0, "items": items}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("company", "currency", "period-start", "as-of", "output"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--data-source", default="Site DB")
    parser.add_argument("--exclude-scheme", action="append", default=[])
    args = parser.parse_args()
    try:
        workbook = build_workbook(args.company, args.currency, args.period_start, args.as_of,
                                  args.data_source, args.exclude_scheme)
    except ValueError as exc:
        parser.error(str(exc))
    with Path(args.output).open("x", encoding="utf-8") as output:
        json.dump(workbook, output, indent=2, ensure_ascii=False)
        output.write("\n")


if __name__ == "__main__":
    main()
