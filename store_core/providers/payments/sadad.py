"""Sadad (سداد, Almadar Aljadid mobile wallet): still a stub, now wired to the real payment service.

**Why this is not implemented.** Unlike Moamalat, whose Lightbox contract is published at
docs.moamalat.net, Sadad's merchant API is only given to merchants under agreement. Writing the HTTP
calls from guesswork would produce code that looks finished and silently mishandles money, so the
gateway-specific parts are left to whoever holds the credentials and the integration guide. The
parts that are *not* gateway-specific — submitting the order, booking the money, idempotency,
zeroing the amount the delivery agent collects — are already done by `services.payments` and are
shared with Moamalat.

**To finish it**, fill in the three marked places below. Everything else can stay as it is.

Configuration (environment variables or site_config.json, never a DocType):

    SADAD_BASE_URL      merchant API base URL from the integration guide
    SADAD_MERCHANT_ID   merchant id
    SADAD_API_KEY       api key / client secret

Flow to implement:
1. `initiate(sales_order)` — ask Sadad to charge `sales_order.lamsa_phone` for the order total.
   The wallet sends the customer an OTP. Return
   `PaymentResult(status="otp_required", reference=<transaction id>)`; the storefront then shows an
   OTP field. Keep the transaction id on the order (`lamsa_payment_reference`) so `confirm_otp` can
   find it again.
2. `confirm_otp(sales_order, otp)` — send the OTP, then hand the provider's response to `verify()`.
3. `verify(payload)` — check the response is genuine (signature/HMAC as the guide specifies, compared
   with `hmac.compare_digest`), confirm the amount and the merchant reference, and call
   `services.payments.record_payment`. Add an endpoint in `store_core/api/v1/payments.py` that calls
   `confirm_otp`, in the shape of `moamalat_callback`.

Do not mark an order paid from anything the browser sends on its own: only from a response whose
signature verifies with the merchant secret.
"""

from store_core.providers.payments.base import PaymentProvider, PaymentResult
from store_core.services.settings import get_secret


def config() -> dict:
	return {
		"base_url": (get_secret("sadad_base_url") or "").strip().rstrip("/"),
		"merchant_id": (get_secret("sadad_merchant_id") or "").strip(),
		"api_key": (get_secret("sadad_api_key") or "").strip(),
	}


def is_configured() -> bool:
	c = config()
	return bool(c["base_url"] and c["merchant_id"] and c["api_key"])


class SadadProvider(PaymentProvider):
	label_key = "payment.sadad"
	is_online = True

	def is_available(self) -> bool:
		return False  # not implemented yet, so never offered at checkout

	def initiate(self, sales_order) -> PaymentResult:
		# STEP 1: request the charge and return status="otp_required" with the transaction id.
		raise NotImplementedError(
			"Sadad needs its merchant API details. See store_core/providers/payments/sadad.py"
		)

	def confirm_otp(self, sales_order, otp: str) -> PaymentResult:
		# STEP 2: send the OTP, then return self.verify(<provider response>).
		raise NotImplementedError("Sadad OTP confirmation is not implemented yet")

	def verify(self, payload: dict) -> PaymentResult:
		# STEP 3: check the signature and amount, then:
		#   from store_core.services import payments as payment_service
		#   so = payment_service.find_order(payload["merchant_reference"])
		#   payment_service.record_payment(so, provider=self.code, reference=..., amount=...)
		raise NotImplementedError("Sadad callback verification is not implemented yet")
