"""Online payment callbacks: /api/method/store_core.api.v1.payments.*

These endpoints are reached the same way as the rest of the storefront API: the Next.js server
forwards the gateway's response with the storefront API key, so nothing here is open to the public
internet. Authenticity does not rest on that, though — the payload carries the gateway's SecureHash
and the provider's `verify()` recomputes it with the merchant secret before any money is booked.
"""

import frappe

from store_core.providers.payments import registry as payment_registry
from store_core.services import payments as payment_service
from store_core.services.orders import CheckoutError, system_context
from store_core.utils.api import parse_json, storefront_endpoint


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(20, 600))
def moamalat_callback(payload: str | dict):
	"""Result of a Moamalat Lightbox attempt (complete, error or cancel)."""
	return _verify("moamalat", parse_json(payload, {}))


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(20, 600))
def payment_status(order_no: str, event_id: str):
	"""Has this order been paid? The storefront polls it after a gateway callback.

	`event_id` is the checkout's own id, known only to the browser that placed the order, so an
	order number alone cannot be used to read another customer's order.
	"""
	order_no = str(order_no or "").strip().upper()
	so = payment_service.find_order(order_no)
	if not so or (so.lamsa_event_id or "") != str(event_id or ""):
		raise CheckoutError("order_not_found")
	return {
		"order_no": so.lamsa_order_no,
		"payment_status": so.lamsa_payment_status or payment_service.UNPAID,
		"payment_provider": so.lamsa_payment_provider,
		"status": so.lamsa_status,
	}


def _verify(provider_code: str, payload: dict) -> dict:
	if provider_code not in payment_registry.enabled_codes():
		raise CheckoutError("payment_unavailable")
	if not isinstance(payload, dict) or not payload:
		raise CheckoutError("invalid_request")

	provider = payment_registry.get_provider(provider_code)
	with system_context():
		try:
			result = provider.verify(payload)
		except payment_service.PaymentError as e:
			frappe.db.rollback()
			raise CheckoutError("payment_failed", str(e))

	# Never echo the gateway payload back: the storefront only needs the outcome.
	return {
		"status": result.status,
		"provider": result.provider,
		"order_no": (result.extra or {}).get("order_no"),
		"message": result.message,
	}
