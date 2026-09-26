"""Store configuration and delivery zones: /api/method/store_core.api.v1.store.<name>"""

import frappe
from frappe.utils import cint, flt

from store_core.providers.embeddings import registry as embedder_registry
from store_core.providers.payments import registry as payment_registry
from store_core.services.settings import get_settings
from store_core.utils.api import storefront_endpoint
from store_core.utils.phone import InvalidPhone, normalize_libyan_phone, whatsapp_number


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_config():
	settings = get_settings()
	gift_wrap_fee = frappe.db.get_value(
		"Item Price",
		{"item_code": settings.gift_wrap_item, "price_list": settings.selling_price_list},
		"price_list_rate",
	)
	try:
		whatsapp = whatsapp_number(normalize_libyan_phone(settings.whatsapp_number))
	except InvalidPhone:
		whatsapp = None
	return {
		"store_name": settings.store_name,
		"currency": settings.currency,
		"whatsapp": whatsapp,
		"gift_wrap": {
			"enabled": bool(settings.gift_wrap_item),
			"fee": flt(gift_wrap_fee),
			"message_max_length": cint(settings.gift_message_max_length) or 250,
		},
		"max_qty_per_line": cint(settings.max_qty_per_line) or 10,
		"payment_providers": payment_registry.enabled_providers_info(),
		# Both the setting and the model have to be there, or the storefront would offer a control
		# that can only fail.
		"image_search": bool(cint(settings.image_search_enabled)) and embedder_registry.is_available(),
	}


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_zones():
	"""Delivery zones grouped by city, for the checkout city -> area selects."""
	rows = frappe.get_all(
		"Delivery Zone",
		filters={"enabled": 1},
		fields=["name", "city", "area", "fee", "est_days_min", "est_days_max", "sort_order"],
		order_by="sort_order asc, city asc, area asc",
	)
	cities: dict[str, list] = {}
	for r in rows:
		cities.setdefault(r.city, []).append(
			{
				"zone": r.name,
				"area": r.area,
				"fee": flt(r.fee),
				"est_days_min": cint(r.est_days_min),
				"est_days_max": cint(r.est_days_max),
			}
		)
	return {"cities": [{"city": c, "areas": areas} for c, areas in cities.items()]}
