frappe.ui.form.on("Sidra Contract Profile", {
	refresh(frm) {
		frm.set_intro(__("{0} monthly installments; due day {1}. Agreed-price sales with no additional markup. Penalty, refund and title terms are recorded for the contract document, not calculated or posted by the system.", [cint(frm.doc.installments), cint(frm.doc.due_day)]));
	},
});
