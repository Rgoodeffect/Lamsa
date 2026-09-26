"""Order tracking: /api/method/store_core.api.v1.orders.track_order"""

import frappe

from store_core.services import orders
from store_core.utils.api import storefront_endpoint


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(10, 300))
def track_order(order_no: str, phone: str):
	return orders.track_order(order_no, phone)
