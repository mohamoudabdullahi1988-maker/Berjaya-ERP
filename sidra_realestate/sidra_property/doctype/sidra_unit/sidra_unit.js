// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Reserve Unit / Cancel Reservation actions (SAL-04). The server re-checks roles,
// per-Company permissions and the unit row lock; these buttons only call the APIs.

const SIDRA_RESERVE_ROLES = ["Sidra Sales User", "Sidra Sales Manager"];

frappe.ui.form.on("Sidra Unit", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role(SIDRA_RESERVE_ROLES)) {
			return;
		}
		if (frm.doc.status === "Available") {
			frm.add_custom_button(__("Reserve Unit"), () => sidra_reserve_unit(frm));
		}
		if (frm.doc.status === "Reserved" && frm.doc.current_reservation) {
			frm.add_custom_button(__("Cancel Reservation"), () =>
				sidra_cancel_reservation(frm.doc.current_reservation, () => frm.reload_doc())
			);
		}
	},
});

function sidra_reserve_unit(frm, acknowledged = false) {
	if (!(Number(frm.doc.cash_price) > 0) && !acknowledged) {
		frappe.confirm(__("This unit has no positive asking price. Check its approved Price History before reserving. Continue?"), () => sidra_reserve_unit(frm, true));
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Reserve {0}", [frm.doc.name]),
		fields: [
			{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Customer"), reqd: 1 },
			{ fieldname: "days", fieldtype: "Int", label: __("Days"), default: 7, reqd: 1 },
		],
		primary_action_label: __("Reserve"),
		primary_action(values) {
			if (cint(values.days) < 1) {
				frappe.msgprint(__("A reservation must last at least one day"));
				return;
			}
			frappe
				.call({
					method: "sidra_realestate.services.reservations.reserve_unit",
					type: "POST",
					args: { unit_name: frm.doc.name, customer: values.customer, days: values.days },
					freeze: true,
					freeze_message: __("Reserving..."),
				})
				.then((r) => {
					dialog.hide();
					frappe.show_alert({
						message: __("Reserved as {0} until {1}", [
							r.message.reservation,
							frappe.datetime.str_to_user(r.message.expires_on),
						]),
						indicator: "green",
					});
					frm.reload_doc();
				})
				.catch(() => frm.reload_doc()); // server message already shown (e.g. reserved meanwhile)
		},
	});
	dialog.show();
}

function sidra_cancel_reservation(reservation, after) {
	frappe.confirm(__("Cancel reservation {0} and release the unit?", [reservation]), () =>
		frappe
			.call({
				method: "sidra_realestate.services.reservations.cancel_reservation",
				type: "POST",
				args: { reservation },
				freeze: true,
			})
			.then(() => {
				frappe.show_alert({ message: __("Reservation {0} cancelled", [reservation]), indicator: "orange" });
				after();
			})
			.catch(after)
	);
}

window.sidra_cancel_reservation = sidra_cancel_reservation;

