// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Buyer KYC (SAL-07; decision G12). A Sidra Sales Manager verifies.

frappe.ui.form.on("Sidra Customer KYC", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Verified") return;
		if (frm.doc.id_document && frappe.user.has_role("Sidra Sales Manager")) {
			frm.add_custom_button(__("Verify"), () =>
				frappe
					.call("sidra_realestate.sidra_sales.doctype.sidra_customer_kyc.sidra_customer_kyc.verify_kyc", {
						kyc: frm.doc.name,
					})
					.then(() => frm.reload_doc())
			);
		}
	},
});
