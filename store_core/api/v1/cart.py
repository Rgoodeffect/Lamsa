"""Cart endpoints: /api/method/store_core.api.v1.cart.<name>"""

import frappe
from frappe.utils import cint

from store_core.services import orders
from store_core.utils.api import parse_json, storefront_endpoint


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(120, 60))
def quote(
	items: str | list,
	zone: str | None = None,
	gift_wrap: str | int | bool | None = 0,
	coupon_code: str | None = None,
):
	"""Server-side prices for a cart: items [{item_code, qty}], optional zone, gift wrap and coupon."""
	return orders.quote(
		parse_json(items, []), zone=zone, gift_wrap=bool(cint(gift_wrap)), coupon_code=coupon_code
	)
