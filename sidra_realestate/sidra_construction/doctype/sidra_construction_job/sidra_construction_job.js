// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Construction job: BOQ revisions, variation orders, inspections and stage certification
// (CON-04, CON-05, CON-06; docs/CONSTRUCTION-CONTROLS_v0.1.md). No invoices are created here.

frappe.ui.form.on("Sidra Construction Job", {
	refresh(frm) {
		if (frm.is_new()) return;
		const closed = ["Closed", "Cancelled"].includes(frm.doc.status);

		if (frm.doc.boq_revision) {
			frm.set_df_property("boq", "read_only", 1);
			frm.set_intro(
				__("The BOQ is controlled by approved revision {0}. Change it through a new BOQ Revision.", [
					frm.doc.boq_revision,
				]),
				"blue"
			);
		}
		if ((frm.doc.__onload || {}).has_approved_variations) {
			frm.set_df_property("contract_value", "read_only", 1);
		}

		if (closed) return;
		const make = (doctype) => frappe.new_doc(doctype, { job: frm.doc.name });
		if (frappe.model.can_create("Sidra BOQ Revision")) {
			frm.add_custom_button(__("BOQ Revision"), () => make("Sidra BOQ Revision"), __("Create"));
		}
		if (frappe.model.can_create("Sidra Variation Order")) {
			frm.add_custom_button(__("Variation Order"), () => make("Sidra Variation Order"), __("Create"));
		}
		if (frappe.model.can_create("Sidra Inspection Report")) {
			frm.add_custom_button(__("Inspection Report"), () => make("Sidra Inspection Report"), __("Create"));
		}

		const ready = (frm.doc.stages || []).filter(
			(s) => !s.certified && s.status === "Completed" && flt(s.completion_pct) === 100 && s.actual_end
		);
		if (ready.length && frappe.user.has_role("Sidra Project Manager")) {
			frm.add_custom_button(__("Certify Stage"), () => {
				frappe.prompt(
					{
						fieldname: "stage",
						fieldtype: "Select",
						label: __("Completed stage"),
						options: ready.map((s) => ({ value: s.name, label: `${s.idx}. ${s.stage_name}` })),
						reqd: 1,
						description: __("Certification records completion only. It is not an invoice."),
					},
					({ stage }) =>
						frappe
							.call("sidra_realestate.sidra_construction.doctype.sidra_construction_job.sidra_construction_job.certify_stage", {
								job: frm.doc.name,
								stage,
							})
							.then(() => frm.reload_doc()),
					__("Certify Stage"),
					__("Certify")
				);
			});
		}
	},
});
