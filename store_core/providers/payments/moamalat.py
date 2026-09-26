"""Moamalat (Libya) card payment gateway: documented stub.

Status: NOT IMPLEMENTED. Registered in hooks but disabled until its code is listed in
Lamsa Settings > Enabled Payment Providers.

How to implement (checklist, based on the usual Moamalat Lightbox flow; verify every detail
against the merchant integration guide Moamalat gives you before going live):
1. Credentials in env/site_config only (never in a DocType):
      MOAMALAT_MERCHANT_ID, MOAMALAT_TERMINAL_ID, MOAMALAT_SECRET_KEY (hex), MOAMALAT_ENV=test|live
   Read them with `store_core.services.settings.get_secret("moamalat_merchant_id")`.
2. `initiate(sales_order)`:
   - amount in the smallest unit (LYD has 3 decimals: 1 LYD = 1000 dirham),
   - merchant reference = sales_order.lamsa_order_no,
   - DateTimeLocalTrxn = UTC "yyyyMMddHHmm",
   - SecureHash = HMAC-SHA256 over the sorted "Amount=..&DateTimeLocalTrxn=..&MerchantId=..&
     MerchantReference=..&TerminalId=.." string, keyed with the hex-decoded secret, uppercase hex.
   - return PaymentResult(status="redirect", redirect_url=<Lightbox/hosted page URL>, extra={...}).
     The storefront opens Moamalat Lightbox with the returned parameters.
3. Callback: add a whitelisted, guest, rate-limited endpoint in
   `store_core/api/v1/payments.py` (e.g. `moamalat_callback`) that calls `verify(payload)`:
   - recompute SecureHash from the notification fields and compare with hmac.compare_digest,
   - confirm the amount and MerchantReference match the Sales Order,
   - on success: submit the Sales Order (or mark it paid) and create a Payment Entry via
     erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry("Sales Order", so.name)
     using a bank account for Moamalat settlements.
4. Make the callback idempotent (the gateway may retry).
5. Enable: add "moamalat" to Lamsa Settings > Enabled Payment Providers.
"""

from store_core.providers.payments.base import PaymentProvider, PaymentResult


class MoamalatProvider(PaymentProvider):
	label_key = "payment.moamalat"
	is_online = True

	def initiate(self, sales_order) -> PaymentResult:
		raise NotImplementedError(
			"Moamalat is not implemented yet. See store_core/providers/payments/moamalat.py"
		)

	def verify(self, payload: dict) -> PaymentResult:
		raise NotImplementedError("Moamalat is not implemented yet")
