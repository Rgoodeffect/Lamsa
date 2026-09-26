// Copyright (c) 2026, Lamsa and contributors
// For license information, please see license.txt

const LAMSA_NEXT = {
	New: ["Confirmed", "Cancelled"],
	Confirmed: ["Out for Delivery", "Cancelled"],
	"Out for Delivery": ["Delivered", "Returned"],
};

frappe.ui.form.on("Delivery Assignment", {
	setup(frm) {
		frm.set_query("agent", () => ({ filters: { active: 1 } }));
	},

	refresh(frm) {
		frm.set_indicator_formatter?.("status");
		if (frm.is_new()) return;
		(LAMSA_NEXT[frm.doc.status] || []).forEach((status) => {
			frm.add_custom_button(__(status), () => lamsa_set_status(frm, status), __("Set Status"));
		});
		["sales_order", "delivery_note", "sales_invoice"].forEach((field) => {
			if (frm.doc[field]) {
				const doctype = frappe.meta.get_docfield(frm.doctype, field).options;
				frm.add_custom_button(__(doctype), () => frappe.set_route("Form", doctype, frm.doc[field]), __("View"));
			}
		});
		if (frm.doc.delivery_note) {
			frm.add_custom_button(__("Print Delivery Note"), () => {
				const url = `/printview?doctype=Delivery%20Note&name=${encodeURIComponent(frm.doc.delivery_note)}&format=Lamsa%20Delivery%20Note`;
				window.open(url, "_blank");
			});
		}
	},
});

function lamsa_set_status(frm, status) {
	const apply = (values = {}) => {
		frm.set_value("status", status);
		Object.entries(values).forEach(([k, v]) => frm.set_value(k, v));
		frm.save();
	};
	if (status === "Out for Delivery" && !frm.doc.agent) {
		frappe.prompt(
			{ fieldname: "agent", fieldtype: "Link", options: "Delivery Agent", label: __("Delivery Agent"), reqd: 1,
				get_query: () => ({ filters: { active: 1 } }) },
			(v) => apply(v),
			__("Assign Agent"),
		);
	} else if (status === "Delivered") {
		frappe.prompt(
			{ fieldname: "collected_amount", fieldtype: "Currency", label: __("Collected Amount"), reqd: 1,
				default: frm.doc.expected_amount },
			(v) => apply(v),
			__("Cash Collected"),
		);
	} else {
		frappe.confirm(__("Change status to {0}?", [__(status)]), () => apply());
	}
}
