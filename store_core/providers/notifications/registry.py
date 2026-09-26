import frappe

from store_core.providers.base_registry import ProviderRegistry
from store_core.providers.notifications.base import Message, NotificationChannel

registry = ProviderRegistry("lamsa_notification_channels", "notification")


def get_channel(code: str | None = None) -> NotificationChannel:
	code = code or frappe.get_cached_doc("Lamsa Settings").notification_channel or "log"
	return registry.get(code)


def notify(message: Message, channel: str | None = None) -> dict:
	"""Send and never raise: a failed message must not break an order status change."""
	try:
		return get_channel(channel).send(message)
	except Exception:
		frappe.log_error(title=f"Lamsa notification failed: {message.template}")
		return {"status": "failed"}
