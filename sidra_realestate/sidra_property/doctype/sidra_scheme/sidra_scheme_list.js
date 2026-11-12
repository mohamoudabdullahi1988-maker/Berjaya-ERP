frappe.listview_settings["Sidra Scheme"] = {
	hide_name_column: true,
	onload(list) {
		const render = list.render.bind(list);
		list.render = async function () {
			const snapshot = this.data;
			const names = snapshot.map(row => row.name);
			let counts = {};
			try {
				const r = await frappe.call({method: "sidra_realestate.desk_setup.scheme_summary", args: {names: JSON.stringify(names)}});
				counts = r.message || {};
			} catch { /* Unknown is shown as a dash; never a fabricated zero. */ }
			if (snapshot !== this.data) return;
			for (const row of snapshot) {
				row._unit_count = counts[row.name]?.total;
				row._available_count = counts[row.name]?.available;
			}
			for (const [field, label] of [["_unit_count", "Units"], ["_available_count", "Available"]]) {
				if (!this.columns.some(c => c.df?.fieldname === field)) this.columns.push({type: "Field", df: {fieldname: field, label: __(label), fieldtype: "Int"}});
			}
			render();
		};
	},
	formatters: {
		_unit_count: value => value == null ? "—" : String(value),
		_available_count: value => value == null ? "—" : String(value),
	},
};
