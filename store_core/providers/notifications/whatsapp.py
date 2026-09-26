"""WhatsApp channel: stub ready for WhatsApp Business Cloud API.

To implement:
1. Env/site_config: WHATSAPP_TOKEN (permanent system-user token), WHATSAPP_PHONE_NUMBER_ID,
   WHATSAPP_API_VERSION (e.g. v21.0).
2. Register each key of templates.TEMPLATES as an approved template in Meta (language "ar").
   Business-initiated messages outside the 24h window must use approved templates.
3. POST https://graph.facebook.com/{version}/{phone_number_id}/messages with
   {"messaging_product": "whatsapp", "to": "<218...>", "type": "template",
    "template": {"name": <template>, "language": {"code": "ar"}, "components": [...]}}
4. Keep sending in a background job (already the case: services.events enqueues notifications).
"""

import frappe

from store_core.providers.notifications.base import Message, NotificationChannel
from store_core.providers.notifications.log import LogChannel
from store_core.services.settings import get_secret


class WhatsAppChannel(NotificationChannel):
	def send(self, message: Message) -> dict:
		if not (get_secret("whatsapp_token") and get_secret("whatsapp_phone_number_id")):
			# Not configured yet: fall back to logging on the order so nothing is lost.
			result = LogChannel().send(message)
			result["channel"] = self.code
			result["reason"] = "whatsapp_not_configured"
			return result
		frappe.log_error(
			title="Lamsa WhatsApp: not implemented",
			message=f"WhatsApp credentials are set but sending is not implemented yet ({message.template})",
		)
		return {"status": "failed", "channel": self.code, "reason": "not_implemented"}
