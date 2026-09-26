"""WhatsApp Business Cloud API channel.

Configuration (environment variables or site_config.json, never a DocType):

    WHATSAPP_TOKEN              permanent system-user access token
    WHATSAPP_PHONE_NUMBER_ID    the sender's phone number id from Meta
    WHATSAPP_API_VERSION        optional, defaults to v21.0
    WHATSAPP_FREE_TEXT          optional "1" to send plain text instead of templates (see below)

Templates: business-initiated messages must use a template approved in Meta Business Manager.
Register one template per key of `templates.TEMPLATES`, language `ar`, with the body text of that
key and its placeholders as {{1}}, {{2}}, ... **in the order they appear in the text here**
(`templates_params.placeholders` derives that order, so the two stay in step).

WHATSAPP_FREE_TEXT=1 sends the rendered text as a normal message instead. Meta only delivers that
inside the 24-hour customer service window, so it is for testing, not production.
"""

import frappe
import requests
from frappe.utils import cint

from store_core.providers.notifications import templates_params
from store_core.providers.notifications.base import Message, NotificationChannel
from store_core.providers.notifications.log import LogChannel
from store_core.providers.notifications.templates import render
from store_core.services.settings import get_secret
from store_core.utils.phone import whatsapp_number

DEFAULT_API_VERSION = "v21.0"
TIMEOUT_SECONDS = 15
LANGUAGE = "ar"


class WhatsAppChannel(NotificationChannel):
	def send(self, message: Message) -> dict:
		token = get_secret("whatsapp_token")
		phone_number_id = get_secret("whatsapp_phone_number_id")
		if not (token and phone_number_id):
			# Not configured yet: fall back to logging on the order so nothing is lost.
			result = LogChannel().send(message)
			result["channel"] = self.code
			result["reason"] = "whatsapp_not_configured"
			return result

		version = get_secret("whatsapp_api_version") or DEFAULT_API_VERSION
		url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
		try:
			response = requests.post(
				url,
				json=build_payload(message),
				headers={"Authorization": f"Bearer {token}"},
				timeout=TIMEOUT_SECONDS,
			)
		except requests.RequestException as exc:
			return self._failed(message, "network", str(exc))

		body = _json(response)
		if response.status_code >= 400:
			error = (body.get("error") or {}) if isinstance(body, dict) else {}
			# 131047/131026 = outside the 24h window or not reachable; 132xxx = template problems.
			return self._failed(
				message,
				str(error.get("code") or response.status_code),
				error.get("message") or response.text[:500],
			)

		wamid = _message_id(body)
		_record(message, f"WhatsApp {message.template} → {message.to} ({wamid or 'sent'})")
		return {"status": "sent", "channel": self.code, "reference": wamid}

	def _failed(self, message: Message, code: str, detail: str) -> dict:
		frappe.log_error(
			title=f"Lamsa WhatsApp send failed ({code})",
			message=f"template={message.template} to={message.to}\n{detail}",
		)
		# Keep the text on the order so staff can follow up by hand.
		_record(message, f"WhatsApp {message.template} → {message.to} failed ({code})\n{render(message.template, message.context)}")
		return {"status": "failed", "channel": self.code, "reason": code}


def build_payload(message: Message) -> dict:
	"""Cloud API request body for one order-status message."""
	to = whatsapp_number(message.to)
	if cint(get_secret("whatsapp_free_text")):
		return {
			"messaging_product": "whatsapp",
			"recipient_type": "individual",
			"to": to,
			"type": "text",
			"text": {"preview_url": False, "body": render(message.template, message.context)},
		}

	parameters = [
		{"type": "text", "text": value}
		for value in templates_params.ordered_values(message.template, message.context)
	]
	template: dict = {"name": message.template, "language": {"code": LANGUAGE}}
	if parameters:
		template["components"] = [{"type": "body", "parameters": parameters}]
	return {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to,
		"type": "template",
		"template": template,
	}


def _json(response) -> dict:
	try:
		body = response.json()
	except ValueError:
		return {}
	return body if isinstance(body, dict) else {}


def _message_id(body: dict) -> str | None:
	messages = body.get("messages")
	if isinstance(messages, list) and messages and isinstance(messages[0], dict):
		return messages[0].get("id")
	return None


def _record(message: Message, text: str):
	if not (message.reference_doctype and message.reference_name):
		return
	try:
		frappe.get_doc(message.reference_doctype, message.reference_name).add_comment("Info", text)
	except Exception:
		frappe.log_error(title="Lamsa WhatsApp: could not comment on the order")
