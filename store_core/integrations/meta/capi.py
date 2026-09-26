"""Meta Conversions API (server-side events): stub, ready to switch on.

The storefront Pixel fires `Purchase` with eventID = Sales Order.lamsa_event_id. Sending the same
event_id from the server lets Meta deduplicate browser and server events.

To enable, set in env or site_config:
    META_PIXEL_ID, META_CAPI_ACCESS_TOKEN, (optional) META_CAPI_TEST_EVENT_CODE
Endpoint: POST https://graph.facebook.com/v21.0/{pixel_id}/events
"""

import hashlib
import time

import frappe
import requests
from frappe.utils import flt, get_datetime

from store_core.services.settings import get_secret

GRAPH_VERSION = "v21.0"


def _sha256(value: str | None) -> str | None:
	if not value:
		return None
	return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def build_purchase_event(so) -> dict:
	phone_digits = (so.lamsa_phone or "").lstrip("+")
	settings = frappe.get_cached_doc("Lamsa Settings")
	return {
		"event_name": "Purchase",
		"event_time": int(get_datetime(so.creation).timestamp()) if so.creation else int(time.time()),
		"event_id": so.lamsa_event_id,
		"action_source": "website",
		"event_source_url": (settings.storefront_url or "").rstrip("/") + "/checkout",
		"user_data": {
			"ph": [_sha256(phone_digits)] if phone_digits else [],
			"country": [_sha256("ly")],
			"external_id": [_sha256(so.customer)],
		},
		"custom_data": {
			"currency": so.currency,
			"value": flt(so.rounded_total or so.grand_total),
			"order_id": so.lamsa_order_no,
			"content_type": "product",
			"contents": [
				{"id": i.item_code, "quantity": flt(i.qty), "item_price": flt(i.rate)}
				for i in so.items
				if i.item_code not in (settings.gift_wrap_item, settings.delivery_fee_item)
			],
		},
	}


def send_purchase(so) -> dict:
	pixel_id, token = get_secret("meta_pixel_id"), get_secret("meta_capi_access_token")
	if not (pixel_id and token):
		return {"status": "skipped", "reason": "not_configured"}

	payload = {"data": [build_purchase_event(so)]}
	test_code = get_secret("meta_capi_test_event_code")
	if test_code:
		payload["test_event_code"] = test_code
	try:
		response = requests.post(
			f"https://graph.facebook.com/{GRAPH_VERSION}/{pixel_id}/events",
			params={"access_token": token},
			json=payload,
			timeout=10,
		)
		response.raise_for_status()
		return {"status": "sent"}
	except Exception:
		frappe.log_error(title="Lamsa Meta CAPI failed")
		return {"status": "failed"}
