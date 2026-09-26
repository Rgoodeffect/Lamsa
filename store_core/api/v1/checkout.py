"""Checkout endpoint: /api/method/store_core.api.v1.checkout.place_order"""

import frappe

from store_core.services import orders
from store_core.utils.api import parse_json, storefront_endpoint


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(5, 600))
def place_order(
	items: str | list,
	full_name: str,
	phone: str,
	zone: str,
	event_id: str,
	address_notes: str | None = None,
	gift_wrap: str | int | bool | None = 0,
	gift_message: str | None = None,
	payment_provider: str | None = None,
	source: str | None = None,
):
	return orders.place_order(
		{
			"items": parse_json(items, []),
			"full_name": full_name,
			"phone": phone,
			"zone": zone,
			"event_id": event_id,
			"address_notes": address_notes,
			"gift_wrap": gift_wrap,
			"gift_message": gift_message,
			"payment_provider": payment_provider,
			"source": source,
		}
	)
