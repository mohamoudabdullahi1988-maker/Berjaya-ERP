"""Native read-only supporting report. No raw SQL or permission bypass on parents."""

from html import escape

from frappe import _

from sidra_realestate.api.executive_dashboard import executive_evidence


def execute(filters=None):
	rows = executive_evidence(filters or {})
	# These are evidence rows, not an accounting ledger; explicit unknown values must not format as 0.
	rows = [
		{**row, "value": row.get("value") if row.get("value") is not None else "Unavailable"} for row in rows
	]
	# Native Data columns can render HTML. Keep recorded names/notes literal, including in print views.
	for row in rows:
		for key in ("row_reference", "note", "owner", "status"):
			if isinstance(row.get(key), str):
				row[key] = escape(row[key])
	columns = [
		{"fieldname": "doctype", "label": _("Source type"), "fieldtype": "Data", "hidden": 1},
		{
			"fieldname": "record",
			"label": _("Source record"),
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": 210,
		},
		{"fieldname": "row_reference", "label": _("Source row"), "fieldtype": "Data", "width": 150},
		{"fieldname": "date", "label": _("Recorded date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "status", "label": _("Status / row type"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "value",
			"label": _("Recorded amount / asking price"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 85,
		},
		{"fieldname": "age_days", "label": _("Registration age (days)"), "fieldtype": "Int", "width": 130},
		{"fieldname": "owner", "label": _("Recorded engineer"), "fieldtype": "Data", "width": 180},
		{"fieldname": "note", "label": _("Basis / limitation"), "fieldtype": "Data", "width": 420},
	]
	return (
		columns,
		rows,
		_(
			"Live operational records are re-read with current permissions. Values may change after the dashboard refresh. Amounts are not revenue, receipts or unpaid balances; dates do not certify an approved baseline."
		),
	)
