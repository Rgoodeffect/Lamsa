"""Notification channel interface for order status messages (WhatsApp first, SMS later)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
	to: str  # E.164 phone, e.g. +218912345678
	template: str  # e.g. "order_placed", "order_confirmed", "out_for_delivery", "delivered"
	context: dict
	reference_doctype: str | None = None
	reference_name: str | None = None


class NotificationChannel(ABC):
	code: str = ""

	@abstractmethod
	def send(self, message: Message) -> dict:
		"""Send the message; return {"status": "sent"|"queued"|"skipped"|"failed", ...}."""
