"""Moamalat (Libya) card payments through the Lightbox widget.

https://docs.moamalat.net/lightBox.html

Configuration (environment variables or site_config.json, never a DocType):

    MOAMALAT_MERCHANT_ID    merchant id (MID)
    MOAMALAT_TERMINAL_ID    terminal id (TID)
    MOAMALAT_SECRET_KEY     merchant secret key, hex
    MOAMALAT_ENV            "test" (default) or "live"

Flow:
1. Checkout creates the Draft Sales Order, then `initiate()` returns status "lightbox" with the
   widget parameters and the script URL. Nothing is charged yet.
2. The storefront loads the Lightbox script and opens the widget with those parameters. The
   customer enters their card inside Moamalat's own iframe; card data never touches Lamsa.
3. The widget's completeCallback posts the gateway response to the storefront, which forwards it
   to `store_core.api.v1.payments.moamalat_callback` -> `verify()`.
   The response carries a SecureHash computed with the merchant secret, so a customer cannot forge
   a "paid" result: `verify()` recomputes it and compares in constant time. It then checks that the
   MerchantReference is this order and that the Amount equals the order total.
4. On success `services.payments.record_payment` submits the order and books an advance Payment
   Entry. It is idempotent, because the widget may fire its callback more than once.

An order is only ever marked paid from a callback whose hash verifies, so a failed or abandoned
attempt simply leaves the Draft order for the customer to retry.
"""

from frappe.utils import now_datetime

from store_core.providers.payments import moamalat_hash as mh
from store_core.providers.payments.base import PaymentProvider, PaymentResult
from store_core.services.settings import get_secret

SCRIPT_URLS = {
	"test": "https://tnpg.moamalat.net:6006/js/lightbox.js",
	"live": "https://npg.moamalat.net:6006/js/lightbox.js",
}
TRX_DATETIME_FORMAT = "%Y%m%d%H%M"


def config() -> dict:
	"""Merchant credentials and the environment to talk to."""
	env = (get_secret("moamalat_env") or "test").strip().lower()
	return {
		"merchant_id": (get_secret("moamalat_merchant_id") or "").strip(),
		"terminal_id": (get_secret("moamalat_terminal_id") or "").strip(),
		"secret_key": (get_secret("moamalat_secret_key") or "").strip(),
		"env": env if env in SCRIPT_URLS else "test",
	}


def is_configured() -> bool:
	c = config()
	return bool(c["merchant_id"] and c["terminal_id"] and c["secret_key"])


class MoamalatProvider(PaymentProvider):
	label_key = "payment.moamalat"
	is_online = True

	def is_available(self) -> bool:
		return is_configured()

	def initiate(self, sales_order) -> PaymentResult:
		from store_core.services.payments import order_total

		c = config()
		if not is_configured():
			return PaymentResult(
				status="failed",
				provider=self.code,
				message="moamalat_not_configured",
			)

		amount = order_total(sales_order)
		amount_minor = mh.to_minor_units(amount)
		reference = sales_order.lamsa_order_no
		trx_datetime = now_datetime().strftime(TRX_DATETIME_FORMAT)

		params = mh.lightbox_params(
			c["merchant_id"], c["terminal_id"], amount_minor, reference, trx_datetime, c["secret_key"]
		)
		return PaymentResult(
			status="lightbox",
			provider=self.code,
			reference=reference,
			amount=amount,
			extra={"script_url": SCRIPT_URLS[c["env"]], "environment": c["env"], "params": params},
		)

	def verify(self, payload: dict) -> PaymentResult:
		"""Check a Lightbox callback and, when it is a genuine success, book the payment."""
		from store_core.services import payments as payment_service

		c = config()
		if not is_configured():
			return PaymentResult(status="failed", provider=self.code, message="moamalat_not_configured")
		if not isinstance(payload, dict) or not mh.callback_hash_matches(payload, c["secret_key"]):
			# Either not from Moamalat, or altered on the way here.
			return PaymentResult(status="failed", provider=self.code, message="invalid_signature")

		reference = str(payload.get("MerchantReference") or "").strip()
		so = payment_service.find_order(reference)
		if not so:
			return PaymentResult(status="failed", provider=self.code, message="order_not_found")

		if payload.get("ErrorMessage"):
			payment_service.record_failure(so, self.code, str(payload["ErrorMessage"])[:140])
			return PaymentResult(
				status="failed", provider=self.code, reference=reference, message="payment_failed"
			)

		amount = mh.from_minor_units(payload.get("Amount") or 0)
		if not payment_service.amounts_match(amount, payment_service.order_total(so)):
			return PaymentResult(status="failed", provider=self.code, message="amount_mismatch")

		gateway_reference = str(
			payload.get("SystemReference") or payload.get("NetworkReference") or reference
		)
		result = payment_service.record_payment(
			so,
			provider=self.code,
			reference=gateway_reference,
			amount=amount,
			mode_of_payment=_mode_of_payment(payload),
		)
		return PaymentResult(
			status="paid",
			provider=self.code,
			reference=gateway_reference,
			amount=amount,
			extra={"order_no": so.lamsa_order_no, "duplicate": result["duplicate"]},
		)


def _mode_of_payment(payload: dict) -> str:
	"""Moamalat reports how the customer paid (Card / Tahweel / mVisa)."""
	paid_through = str(payload.get("PaidThrough") or "").strip()
	return paid_through or "Credit Card"
