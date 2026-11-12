frappe.ui.form.on("Sidra Scheme", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Plots and Units"), () => frappe.set_route("List", "Sidra Unit", {scheme: frm.doc.name}), __("Connections"));
		if (frappe.model.can_read("Sidra Sale Contract")) {
			frm.add_custom_button(__("Sale Contracts"), async () => {
				const r = await frappe.call({method: "sidra_realestate.desk_setup.scheme_summary", args: {names: JSON.stringify([frm.doc.name])}});
				const names = r.message?.[frm.doc.name]?.contracts || [];
				if (!names.length) return frappe.msgprint(__("No accessible sale contracts for this scheme."));
				frappe.set_route("List", "Sidra Sale Contract", {name: ["in", names]});
			}, __("Connections"));
		}
	},
});
