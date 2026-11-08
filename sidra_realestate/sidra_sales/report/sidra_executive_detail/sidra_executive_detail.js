frappe.query_reports["Sidra Executive Detail"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "period", label: __("Sales reporting period"), fieldtype: "Select", options: [
			{value:"this_month",label:__("This month")},{value:"last_30_days",label:__("Last 30 days")},{value:"last_90_days",label:__("Last 90 days")}
		], default: "this_month", reqd: 1 },
		{ fieldname: "metric", label: __("Supporting cohort"), fieldtype: "Select", options: [
			{value:"sales_value",label:__("Confirmed sales")},{value:"available_units",label:__("Available units")},
			{value:"scheduled_dues",label:__("Gross scheduled dues")},{value:"stage_exceptions",label:__("Recorded stage date exceptions")},
			{value:"reservations_due",label:__("Active reservations past expiry")},{value:"inventory_age",label:__("Inventory registration age")},
			{value:"cancelled_contracts",label:__("Cancelled contract records")}
		], default: "sales_value", reqd: 1 },
		{ fieldname: "as_of", label: __("Dashboard date (Mogadishu)"), fieldtype: "Date" },
	],
};
