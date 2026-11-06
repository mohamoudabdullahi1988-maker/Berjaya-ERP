// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Cancel Reservation action (SAL-04); the server re-checks roles and permissions.

frappe.ui.form.on("Sidra Reservation", {
	refresh(frm) {
		frm.disable_save(); // reservations change only through the actions
		if (
			frm.doc.status === "Active" &&
			frappe.user.has_role(["Sidra Sales User", "Sidra Sales Manager"])
		) {
			frm.add_custom_button(__("Cancel Reservation"), () =>
				frappe.confirm(__("Cancel reservation {0} and release the unit?", [frm.doc.name]), () =>
					frappe
						.call({
							method: "sidra_realestate.services.reservations.cancel_reservation",
							type: "POST",
							args: { reservation: frm.doc.name },
							freeze: true,
						})
						.then(() => frm.reload_doc())
						.catch(() => frm.reload_doc())
				)
			);
		}
	},
});
