frappe.ui.form.on("Sidra Contract Clause", {
	refresh(frm) {
		if (!String(frm.doc.text_so || "").trim() || !String(frm.doc.text_en || "").trim()) {
			frm.set_intro(__("Wording is incomplete. Sidra must supply both Somali and English text before General Manager approval. Do not use this clause as approved wording."), "orange");
		} else {
			frm.set_intro("");
		}
	},
});
