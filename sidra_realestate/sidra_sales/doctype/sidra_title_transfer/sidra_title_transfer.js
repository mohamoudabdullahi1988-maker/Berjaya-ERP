// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Title transfer tracker (SAL-08, SAL-18; decision G12). Record only.

frappe.ui.form.on("Sidra Title Transfer", {
	setup(frm) {
		frm.set_query("contract", () => ({ filters: { docstatus: 1 } }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		const base = "sidra_realestate.sidra_sales.doctype.sidra_title_transfer.sidra_title_transfer.";
		const call = (method) => frappe.call(base + method, { title: frm.doc.name }).then(() => frm.reload_doc());
		const colour = { "Due Soon": "orange", Overdue: "red", "Handed Over Late": "red" }[frm.doc.status];
		if (colour) {
			frm.dashboard.set_headline_alert(
				frm.doc.days_overdue
					? __("{0}: {1} day(s) past the title deadline", [__(frm.doc.status), frm.doc.days_overdue])
					: __("Title deadline {0}", [frappe.datetime.str_to_user(frm.doc.deadline_date)]),
				colour
			);
		}
		if (
			!frm.doc.final_payment_confirmed_on &&
			frm.doc.final_payment_date &&
			frm.doc.final_payment_evidence &&
			frappe.user.has_role("Sidra Sales Manager") &&
			frappe.session.user !== frm.doc.final_payment_entered_by
		) {
			frm.add_custom_button(__("Confirm Final Payment"), () => call("confirm_final_payment"));
		}
		if (
			frm.doc.final_payment_confirmed_on &&
			!frm.doc.handover_confirmed_on &&
			frm.doc.handed_over_on &&
			frm.doc.handover_evidence &&
			frappe.user.has_role("Sidra General Manager")
		) {
			frm.add_custom_button(__("Confirm Handover"), () => call("confirm_handover"));
		}
	},
});
