import frappe

from store_core.providers.base_registry import ProviderRegistry
from store_core.providers.payments.base import PaymentProvider

registry = ProviderRegistry("lamsa_payment_providers", "payment")


def get_provider(code: str) -> PaymentProvider:
	return registry.get(code)


def enabled_codes() -> list[str]:
	"""Providers registered in hooks AND enabled in Lamsa Settings (one code per line)."""
	settings = frappe.get_cached_doc("Lamsa Settings")
	enabled = [c.strip() for c in (settings.enabled_payment_providers or "cod").splitlines() if c.strip()]
	registered = set(registry.codes())
	return [c for c in enabled if c in registered]


def enabled_providers_info() -> list[dict]:
	return [get_provider(code).public_info() for code in enabled_codes()]
