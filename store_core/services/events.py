"""Background side effects of order events (run via frappe.enqueue after commit)."""

import frappe
from frappe.utils import cint, flt

from store_core.providers.notifications.base import Message
from store_core.providers.notifications.registry import notify
from store_core.providers.notifications.templates import STATUS_TEMPLATES
from store_core.services import catalog, revalidate


def order_placed(sales_order: str):
	so = frappe.get_doc("Sales Order", sales_order)
	# Draft orders hold stock (see catalog.load_stock), so product availability changed.
	catalog.invalidate_index()
	revalidate.request_revalidation(["products"])
	send_status_message(so, "order_placed")

	from store_core.integrations.meta import capi

	capi.send_purchase(so)


def status_changed(sales_order: str, status: str):
	so = frappe.get_doc("Sales Order", sales_order)
	catalog.invalidate_index()
	template = STATUS_TEMPLATES.get(status)
	if template:
		send_status_message(so, template)
	if status == "Delivered":
		reward_coupon(so)


def reward_coupon(so):
	"""A completed order may earn a coupon for the next one; tell the customer when it does."""
	from store_core.services import coupons

	coupon = coupons.grant_reward(so)
	if not coupon:
		return
	send_status_message(so, "coupon_earned", extra={
		"coupon_code": coupon["code"],
		"coupon_percent": f"{flt(coupon['percent']):g}",
		"coupon_valid_upto": coupon["valid_upto"],
	})


def send_status_message(so, template: str, extra: dict | None = None) -> dict:
	if not so.lamsa_phone:
		return {"status": "skipped"}
	zone = frappe.db.get_value(
		"Delivery Zone", so.lamsa_delivery_zone, ["est_days_min", "est_days_max"], as_dict=True
	)
	eta = ""
	if zone:
		eta = (
			f"{cint(zone.est_days_min)}-{cint(zone.est_days_max)} أيام"
			if cint(zone.est_days_max) > cint(zone.est_days_min)
			else f"{cint(zone.est_days_max)} يوم"
		)
	return notify(
		Message(
			to=so.lamsa_phone,
			template=template,
			context={
				"customer_name": so.customer_name,
				"order_no": so.lamsa_order_no,
				"grand_total": f"{flt(so.rounded_total or so.grand_total):,.2f}",
				"currency": "د.ل" if so.currency == "LYD" else so.currency,
				"eta": eta,
				**(extra or {}),
			},
			reference_doctype="Sales Order",
			reference_name=so.name,
		)
	)
