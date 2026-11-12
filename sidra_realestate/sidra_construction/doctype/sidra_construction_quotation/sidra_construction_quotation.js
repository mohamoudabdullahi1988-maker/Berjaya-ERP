// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Construction quotation (CON-02, CON-03; decision G11). The General Manager approves the contract.

frappe.ui.form.on("Sidra Construction Quotation", {
	refresh(frm) {
		const ready =
			frm.doc.docstatus === 1 &&
			!frm.doc.contract_approved_on &&
			frm.doc.client_accepted_on &&
			frm.doc.client_acceptance_document;
		if (ready && frappe.user.has_role("Sidra General Manager")) {
			frm.add_custom_button(__("Approve Contract"), () =>
				frappe.confirm(
					__("Make this quotation the job's contract? This sets the job's contract value, dates and retention."),
					() =>
						frappe
							.call(
								"sidra_realestate.sidra_construction.doctype.sidra_construction_quotation.sidra_construction_quotation.approve_contract",
								{ quotation: frm.doc.name }
							)
							.then(() => frm.reload_doc())
				)
			);
		}
	},
});
