"""Mobile page for delivery agents: /agent (login required, role "Lamsa Delivery Agent")."""

import frappe
from frappe import _
from frappe.utils import flt, today

from store_core.utils.phone import local_format

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/agent"
		raise frappe.Redirect
	if "Lamsa Delivery Agent" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError(_("Only delivery agents can open this page"))

	agent = frappe.db.get_value(
		"Delivery Agent",
		{"user": frappe.session.user, "active": 1},
		["name", "agent_name", "cash_in_hand"],
		as_dict=True,
	)
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.title = _("My Deliveries")
	context.agent = agent
	context.assignments = []
	if not agent:
		return context

	rows = frappe.get_all(
		"Delivery Assignment",
		filters={"agent": agent.name, "status": ["in", ["Confirmed", "Out for Delivery"]]},
		fields=[
			"name",
			"order_no",
			"status",
			"customer_name",
			"phone",
			"address",
			"zone",
			"expected_amount",
			"gift_wrap",
			"gift_message",
			"sales_order",
			"notes",
		],
		order_by="status desc, creation asc",
	)
	delivered_today = frappe.get_all(
		"Delivery Assignment",
		filters={"agent": agent.name, "status": "Delivered", "status_changed_on": [">=", today()]},
		fields=["name", "order_no", "status", "customer_name", "collected_amount"],
	)
	for row in rows:
		row.phone_display = local_format(row.phone) if row.phone else ""
		row.items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": row.sales_order},
			fields=["item_name", "qty"],
			order_by="idx asc",
		)
		row.expected_amount = flt(row.expected_amount)
	context.assignments = rows
	context.delivered_today = delivered_today
	return context
