// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
frappe.listview_settings["Sidra Title Transfer"] = {
	get_indicator(doc) {
		const colours = {
			"Awaiting Final Payment": "gray",
			"No Deadline on Contract": "gray",
			"In Progress": "blue",
			"Due Soon": "orange",
			Overdue: "red",
			"Handed Over": "green",
			"Handed Over Late": "red",
		};
		return [__(doc.status), colours[doc.status] || "gray", "status,=," + doc.status];
	},
};
