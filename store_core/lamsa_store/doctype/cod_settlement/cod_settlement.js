// Copyright (c) 2026, Lamsa and contributors
// For license information, please see license.txt

frappe.ui.form.on("COD Settlement", {
	setup(frm) {
		frm.set_query("cash_account", () => ({
			filters: { company: frm.doc.company, account_type: "Cash", is_group: 0 },
		}));
		frm.set_query("assignment", "items", () => ({
			filters: { agent: frm.doc.agent, status: "Delivered", settled: 0 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.agent) {
			frm.add_custom_button(__("Get Unsettled Orders"), () => {
				frappe
					.call("store_core.lamsa_store.doctype.cod_settlement.cod_settlement.get_unsettled", {
						agent: frm.doc.agent,
					})
					.then(({ message }) => {
						frm.clear_table("items");
						(message || []).forEach((row) => frm.add_child("items", row));
						frm.refresh_field("items");
						frm.trigger("calculate_total");
					});
			});
		}
	},

	agent(frm) {
		frm.refresh();
	},

	calculate_total(frm) {
		frm.set_value(
			"total_amount",
			(frm.doc.items || []).reduce((sum, row) => sum + flt(row.amount), 0),
		);
	},
});

frappe.ui.form.on("COD Settlement Item", {
	amount: (frm) => frm.trigger("calculate_total"),
	items_remove: (frm) => frm.trigger("calculate_total"),
});
