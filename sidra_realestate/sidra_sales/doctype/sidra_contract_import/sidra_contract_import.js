// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Validate (dry run) and Import actions (decision G5).

const SCI_METHOD = "sidra_realestate.sidra_sales.doctype.sidra_contract_import.sidra_contract_import.";

function sci_call(frm, method) {
	return frappe
		.call({ method: SCI_METHOD + method, type: "POST", args: { name: frm.doc.name }, freeze: true })
		.then((r) => {
			frm.reload_doc();
			const ok = r.message && r.message.status !== "Failed";
			frappe.msgprint({ title: r.message.status, message: frappe.utils.escape_html(r.message.log).replace(/\n/g, "<br>"), indicator: ok ? "green" : "red" });
		});
}

frappe.ui.form.on("Sidra Contract Import", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.import_file) {
			return;
		}
		frm.add_custom_button(__("Validate"), () => sci_call(frm, "validate_import"));
		if (frm.doc.status === "Validated") {
			frm.add_custom_button(__("Import"), () => sci_call(frm, "run_import")).addClass("btn-primary");
		}
	},
});
