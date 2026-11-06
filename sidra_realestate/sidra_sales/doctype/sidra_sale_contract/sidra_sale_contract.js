// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Revise Draft action (review finding 5; docs/CONTRACT-REVISION_v0.1.md).

frappe.ui.form.on("Sidra Sale Contract", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0 || !frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(__("Revise Draft"), () =>
			frappe.confirm(
				__(
					"Make a new draft with the profile's current terms and clause wording? This draft stays as it is. The signed copy is not copied."
				),
				() =>
					frappe
						.call({
							method: "sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract.revise_draft",
							type: "POST",
							args: { contract: frm.doc.name },
							freeze: true,
						})
						.then((r) => frappe.set_route("Form", "Sidra Sale Contract", r.message))
			)
		);
	},
});
