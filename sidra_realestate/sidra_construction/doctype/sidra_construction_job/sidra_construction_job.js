// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Construction job: BOQ revisions, variation orders, inspections and stage certification
// (CON-04, CON-05, CON-06; docs/CONSTRUCTION-CONTROLS_v0.2.md). No invoices are created here.

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

		if (closed) return;
		const make = (doctype) => frappe.new_doc(doctype, { job: frm.doc.name });
		if (!frm.doc.contract_quotation && frappe.model.can_create("Sidra Construction Quotation")) {
			frm.add_custom_button(__("Quotation"), () => make("Sidra Construction Quotation"), __("Create"));
		}
		if (frappe.model.can_create("Sidra BOQ Revision")) {
			frm.add_custom_button(__("BOQ Revision"), () => make("Sidra BOQ Revision"), __("Create"));
		}
		if (frm.doc.contract_quotation && frappe.model.can_create("Sidra Variation Order")) {
			frm.add_custom_button(__("Variation Order"), () => make("Sidra Variation Order"), __("Create"));
		}
		if (frappe.model.can_create("Sidra Inspection Report")) {
			frm.add_custom_button(__("Inspection Report"), () => make("Sidra Inspection Report"), __("Create"));
		}
		// G37: one ERPNext Project per job, one Task per stage; the Tasks follow the stages.
		if (
			!frm.doc.project &&
			(frm.doc.stages || []).length &&
			frappe.model.can_create("Project") &&
			frappe.model.can_create("Task")
		) {
			frm.add_custom_button(
				__("Project"),
				() =>
					frappe.confirm(
						__("Create an ERPNext Project for this job, with one Task per stage? The Tasks will follow the job's stages from now on."),
						() =>
							frappe
								.call({
									method: "sidra_realestate.services.construction_projects.create_project",
									args: { job: frm.doc.name },
									freeze: true,
								})
								.then(() => frm.reload_doc())
					),
				__("Create")
			);
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
