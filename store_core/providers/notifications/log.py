import frappe

from store_core.providers.notifications.base import Message, NotificationChannel
from store_core.providers.notifications.templates import render


class LogChannel(NotificationChannel):
	"""Default channel: records the message as a Comment on the order instead of sending it."""

	def send(self, message: Message) -> dict:
		text = render(message.template, message.context)
		if message.reference_doctype and message.reference_name:
			frappe.get_doc(message.reference_doctype, message.reference_name).add_comment(
				"Info", f"[{message.template} → {message.to}]\n{text}"
			)
		return {"status": "skipped", "channel": self.code, "text": text}
