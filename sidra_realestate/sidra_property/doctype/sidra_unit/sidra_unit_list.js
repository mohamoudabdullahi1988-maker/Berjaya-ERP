frappe.listview_settings["Sidra Unit"] = {
	hide_name_column: true,
	formatters: {cash_price: (value, df, doc) => Number(value) > 0 ? frappe.format(value, df, null, doc) : __("Not priced")},
};
