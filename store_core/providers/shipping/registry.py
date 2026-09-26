import frappe

from store_core.providers.base_registry import ProviderRegistry
from store_core.providers.shipping.base import ShippingProvider

registry = ProviderRegistry("lamsa_shipping_providers", "shipping")


def get_provider(code: str | None = None) -> ShippingProvider:
	code = code or frappe.get_cached_doc("Lamsa Settings").shipping_provider or "manual"
	return registry.get(code)
