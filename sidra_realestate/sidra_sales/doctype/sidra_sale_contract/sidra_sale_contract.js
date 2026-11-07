// Copyright (c) 2026, Mohamoud Abdullahi Sheikh
// Revise Draft action (review finding 5; docs/CONTRACT-REVISION_v0.1.md).
// Contract capture (docs/CONTRACT-CAPTURE_v0.3.md): Fill Schedule, totals indicator, acknowledgement
// of a schedule difference within the tolerance before confirming (D3).

const SSC_METHOD = "sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract.";
const EXTERNAL = "External (registered)";

function is_external(frm) {
	return frm.doc.contract_type === "Installment" && frm.doc.source === EXTERNAL;
}

function propose(frm, replace, down_payment) {
	return frappe
		.call({
			method: SSC_METHOD + "propose_schedule",
			type: "POST",
			args: { contract: frm.doc.name, replace: replace ? 1 : 0, down_payment },
			freeze: true,
		})
		.then(() => frm.reload_doc());
}

function fill_schedule(frm) {
	const ask_down = (replace) => {
		if (frm.doc.down_payment_mode !== "Included in schedule") {
			return propose(frm, replace);
		}
		frappe.prompt(
			{ fieldname: "down_payment", fieldtype: "Currency", label: __("Down payment amount"), reqd: 1 },
			(values) => propose(frm, replace, values.down_payment),
			__("Down payment row")
		);
	};
	const rows = (frm.doc.schedule || []).length;
	if (rows) {
		frappe.confirm(__("Replace the {0} existing rows?", [rows]), () => ask_down(true));
	} else {
		ask_down(false);
	}
}

frappe.ui.form.on("Sidra Sale Contract", {
	refresh(frm) {
		if (is_external(frm) && frm.doc.schedule_difference) {
			frm.dashboard.set_headline_alert(
				__("Schedule differs from the amount due by {0}", [
					format_currency(frm.doc.schedule_difference, frm.doc.currency),
				]),
				"orange"
			);
		}
		if (frm.is_new() || frm.doc.docstatus !== 0 || !frm.has_perm("write")) {
			return;
		}
		if (is_external(frm)) {
			frm.add_custom_button(__("Fill Schedule"), () => fill_schedule(frm));
			return;
		}
		frm.add_custom_button(__("Revise Draft"), () =>
			frappe.confirm(
				__(
					"Make a new draft with the profile's current terms and clause wording? This draft stays as it is. The signed copy is not copied."
				),
				() =>
					frappe
						.call({
							method: SSC_METHOD + "revise_draft",
							type: "POST",
							args: { contract: frm.doc.name },
							freeze: true,
						})
						.then((r) => frappe.set_route("Form", "Sidra Sale Contract", r.message))
			)
		);
	},

	before_submit(frm) {
		const difference = flt(frm.doc.schedule_difference, 2);
		if (!is_external(frm) || !difference) {
			return;
		}
		return new Promise((resolve, reject) => {
			frappe.confirm(
				__(
					"The schedule differs from the amount due by {0}. Confirm the contract with this difference? It is recorded in the contract.",
					[format_currency(difference, frm.doc.currency)]
				),
				resolve,
				() => reject(new Error(__("Confirmation cancelled")))
			);
		});
	},
});
