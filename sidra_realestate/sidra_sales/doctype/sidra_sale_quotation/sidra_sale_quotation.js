// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Sale quotation (SAL-05; decision G13). Offer only: no reservation, contract or posting.

frappe.ui.form.on("Sidra Sale Quotation", {
	setup(frm) {
		frm.set_query("unit", "units", () => ({ filters: { status: ["in", ["Available", "Reserved"]] } }));
		frm.set_query("contract_profile", () => ({ filters: { active: 1, legal_hold: 0 } }));
	},
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0) return;
		const level = frm.doc.discount_approval;
		if (!level || level === "Not Needed") return;
		if (frm.doc.discount_approved_on) {
			frm.dashboard.set_headline_alert(
				__("Discount approved by {0}", [frm.doc.discount_approved_by]),
				"green"
			);
			return;
		}
		frm.dashboard.set_headline_alert(
			__("The discount needs approval by the {0} before this quotation can be issued", [
				__(level.replace("Sidra ", "")),
			]),
			"orange"
		);
		const may =
			frappe.user.has_role("Sidra General Manager") ||
			(level === "Sidra Sales Manager" && frappe.user.has_role("Sidra Sales Manager"));
		if (may && frappe.session.user !== frm.doc.owner) {
			frm.add_custom_button(__("Approve Discount"), () =>
				frappe
					.call(
						"sidra_realestate.sidra_sales.doctype.sidra_sale_quotation.sidra_sale_quotation.approve_discount",
						{ quotation: frm.doc.name }
					)
					.then(() => frm.reload_doc())
			);
		}
	},
});
