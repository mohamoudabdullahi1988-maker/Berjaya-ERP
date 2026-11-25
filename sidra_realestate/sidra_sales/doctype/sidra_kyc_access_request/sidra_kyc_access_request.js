// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// G32: the General Manager approves, refuses or revokes access to one buyer's identity record.

const KYC_ACCESS = "sidra_realestate.sidra_sales.doctype.sidra_kyc_access_request.sidra_kyc_access_request";

frappe.ui.form.on("Sidra KYC Access Request", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("Sidra General Manager")) return;
		const call = (method, args) =>
			frappe.call({ method: `${KYC_ACCESS}.${method}`, args: { name: frm.doc.name, ...args }, freeze: true }).then(() => frm.reload_doc());

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Approve"), () =>
				frappe.prompt(
					[
						{
							fieldname: "valid_until",
							fieldtype: "Date",
							label: __("Access until"),
							reqd: 1,
							default: frappe.datetime.add_days(frappe.datetime.get_today(), 30),
							description: __("Read and download only. Access ends at the end of this day."),
						},
						{ fieldname: "note", fieldtype: "Small Text", label: __("Note") },
					],
					(values) => call("approve", values),
					__("Approve identity access"),
					__("Approve")
				)
			);
			frm.add_custom_button(__("Refuse"), () =>
				frappe.prompt(
					{ fieldname: "note", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
					(values) => call("refuse", values),
					__("Refuse identity access"),
					__("Refuse")
				)
			);
		}
		if (frm.doc.status === "Approved") {
			frm.add_custom_button(__("Revoke"), () =>
				frappe.prompt(
					{ fieldname: "note", fieldtype: "Small Text", label: __("Reason") },
					(values) => call("revoke", values),
					__("Revoke identity access"),
					__("Revoke")
				)
			);
		}
	},
});
