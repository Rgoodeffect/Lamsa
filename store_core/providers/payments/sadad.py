"""Sadad (Libyan Almadar mobile wallet) payment: documented stub.

Status: NOT IMPLEMENTED. Registered in hooks but disabled until listed in
Lamsa Settings > Enabled Payment Providers.

Typical flow for OTP wallet gateways in Libya (confirm against the provider's current API docs):
1. Credentials in env/site_config: SADAD_API_KEY, SADAD_MERCHANT_ID, SADAD_BASE_URL.
2. `initiate(sales_order)`: request a payment for the customer's mobile (sales_order.lamsa_phone)
   and amount; the wallet sends an OTP to the customer. Return
   PaymentResult(status="otp_required", reference=<transaction id>).
3. Add an endpoint `store_core.api.v1.payments.confirm_otp(order_no, otp)` that calls the
   provider's confirm API, then `verify(...)`.
4. On success create a Payment Entry against the Sales Order (see moamalat.py step 3).
"""

from store_core.providers.payments.base import PaymentProvider, PaymentResult


class SadadProvider(PaymentProvider):
	label_key = "payment.sadad"
	is_online = True

	def initiate(self, sales_order) -> PaymentResult:
		raise NotImplementedError("Sadad is not implemented yet. See store_core/providers/payments/sadad.py")

	def verify(self, payload: dict) -> PaymentResult:
		raise NotImplementedError("Sadad is not implemented yet")
