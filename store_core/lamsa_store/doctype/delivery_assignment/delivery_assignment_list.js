frappe.listview_settings["Delivery Assignment"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			New: "blue",
			Confirmed: "purple",
			"Out for Delivery": "orange",
			Delivered: "green",
			Returned: "gray",
			Cancelled: "red",
		};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
