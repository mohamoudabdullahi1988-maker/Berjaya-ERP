"""Recorded lead activity, without inferring qualification or conversion."""


def lead_status_summary(rows):
	counts = {}
	for row in rows:
		status = row.get("status") or "Unspecified"
		counts[status] = counts.get(status, 0) + 1
	return {
		"available": True,
		"basis": "recorded_lead_status",
		"notice": "Readable leads created in the selected period, grouped by recorded status. Qualification and conversion are not configured.",
		"qualified_opportunities": None,
		"conversion_rate": None,
		"pipeline": [{"label": status, "value": count} for status, count in sorted(counts.items())],
	}


def sales_activity(company, start, today):
	import frappe
	from frappe.utils import get_system_timezone

	from sidra_realestate.services.executive_metrics import site_period_bounds

	missing = {"available": False, "reason": "Your role cannot read lead activity."}
	if not frappe.has_permission("Lead", "read"):
		return missing
	first, last = site_period_bounds(start, today, get_system_timezone())
	try:
		rows = frappe.get_list(
			"Lead",
			filters={"company": company, "creation": ["between", [first, last]]},
			fields=["name", "status"],
			limit_page_length=0,
		)
	except frappe.PermissionError:
		return missing
	return lead_status_summary(rows)
