import frappe

from store_core.providers.base_registry import ProviderRegistry
from store_core.providers.payments.base import PaymentProvider

registry = ProviderRegistry("lamsa_payment_providers", "payment")


def get_provider(code: str) -> PaymentProvider:
	return registry.get(code)


def enabled_codes() -> list[str]:
	"""Providers registered in hooks, enabled in Lamsa Settings (one code per line) and configured.

	A gateway listed in the settings but missing its credentials is left out, so the checkout never
	offers a payment method that cannot be completed.
	"""
	settings = frappe.get_cached_doc("Lamsa Settings")
	enabled = [c.strip() for c in (settings.enabled_payment_providers or "cod").splitlines() if c.strip()]
	registered = set(registry.codes())
	return [c for c in enabled if c in registered and _available(c)]


def _available(code: str) -> bool:
	try:
		return get_provider(code).is_available()
	except Exception:
		frappe.log_error(title=f"Lamsa: payment provider {code} could not be loaded")
		return False


def enabled_providers_info() -> list[dict]:
	return [get_provider(code).public_info() for code in enabled_codes()]
