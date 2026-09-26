"""Payment provider interface.

Lifecycle for an order:
1. Checkout creates a Draft Sales Order, then calls `initiate(sales_order)`.
   - Offline methods (COD) return status "pending" and the order proceeds.
   - Online gateways return status "redirect" with a `redirect_url` the storefront sends the
     customer to.
2. The gateway calls back (webhook) -> `verify(payload)` returns a PaymentResult with the
   reference and paid amount. On success the provider records a Payment Entry against the order
   (see `record_payment`).
3. `refund(...)` is used by staff for online payments. COD refunds are handled in cash.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field


@dataclass
class PaymentResult:
	#: "pending"  offline, nothing to do (cash on delivery)
	#: "redirect" send the customer to `redirect_url`
	#: "lightbox" open an embedded gateway widget with `extra` (Moamalat)
	#: "otp_required" the customer must confirm a code (wallet gateways)
	#: "paid" / "failed" the outcome of a verified callback
	status: str
	provider: str
	redirect_url: str | None = None
	reference: str | None = None
	amount: float | None = None
	message: str | None = None
	extra: dict = field(default_factory=dict)

	def as_dict(self) -> dict:
		return asdict(self)


class PaymentProvider(ABC):
	code: str = ""
	#: shown in the storefront as a translation key, e.g. "payment.cod"
	label_key: str = ""
	#: True when the customer pays before delivery (card, wallet)
	is_online: bool = False

	@abstractmethod
	def initiate(self, sales_order) -> PaymentResult:
		"""Start payment for a Draft Sales Order."""

	def verify(self, payload: dict) -> PaymentResult:
		"""Validate a gateway callback/webhook. Offline providers do not need it."""
		raise NotImplementedError(f"{self.code} does not accept callbacks")

	def refund(self, sales_order, amount: float, reason: str | None = None) -> PaymentResult:
		raise NotImplementedError(f"{self.code} does not support refunds")

	def is_available(self) -> bool:
		"""Can this provider actually take a payment right now?

		An online provider whose credentials are missing must not be offered at checkout: the
		customer would place a card order that nothing can charge. Offline providers are always
		available.
		"""
		return True

	def public_info(self) -> dict:
		return {"code": self.code, "label_key": self.label_key, "is_online": self.is_online}
