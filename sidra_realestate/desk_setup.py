"""Targeted repair of existing Sidra Desk charts; no financial data changes."""

import frappe


def repair_desk():
	for name, group in (
		("Sidra Units by Status", "status"),
		("Sidra Units by Scheme", "scheme_code"),
		("Sidra Construction Jobs by Status", "status"),
		("Construction Jobs by Status", "status"),
	):
		if not frappe.db.exists("Dashboard Chart", name):
			continue
		chart = frappe.get_doc("Dashboard Chart", name)
		if chart.document_type not in ("Sidra Unit", "Sidra Construction Job"):
			continue
		chart.db_set(
			{
				"chart_type": "Group By",
				"group_by_type": "Count",
				"group_by_based_on": group,
				"aggregate_function_based_on": None,
				"value_based_on": None,
				"currency": None,
			}
		)
		frappe.cache.delete_key(f"chart-data:{name}")
	# Display labels live on Workspace child rows; preserve chart IDs and references.
	for workspace_name in frappe.get_all("Workspace", filters={"module": ["like", "Sidra %"]}, pluck="name"):
		workspace = frappe.get_doc("Workspace", workspace_name)
		for row in workspace.get("charts", []):
			if row.label and row.label.startswith("Sidra "):
				row.db_set("label", row.label.removeprefix("Sidra "))
	frappe.clear_cache()


@frappe.whitelist()
def scheme_summary(names):
	"""Counts and links obey record and Company permissions, including direct calls."""
	names = frappe.parse_json(names)
	if not isinstance(names, list) or len(names) > 500:
		frappe.throw("Select at most 500 schemes")
	allowed = frappe.get_list(
		"Sidra Scheme", filters={"name": ["in", names]}, pluck="name", limit_page_length=500
	)
	result = {name: {"total": None, "available": None, "contracts": []} for name in allowed}
	if frappe.has_permission("Sidra Unit", "read"):
		for name in allowed:
			rows = frappe.get_list(
				"Sidra Unit", filters={"scheme": name}, fields=["name", "status"], limit_page_length=0
			)
			result[name].update(total=len(rows), available=sum(row.status == "Available" for row in rows))
	if frappe.has_permission("Sidra Sale Contract", "read"):
		for name in allowed:
			result[name]["contracts"] = frappe.get_list(
				"Sidra Sale Contract",
				filters=[["Sidra Contract Unit", "scheme", "=", name]],
				pluck="name",
				distinct=True,
				limit_page_length=0,
			)
	return result
