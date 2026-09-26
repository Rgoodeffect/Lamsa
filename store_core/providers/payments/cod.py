from frappe.utils import flt

from store_core.providers.payments.base import PaymentProvider, PaymentResult


class CashOnDelivery(PaymentProvider):
	"""Cash on delivery: nothing to do at checkout.

	The agent collects cash on delivery (Delivery Assignment.collected_amount) and the office
	settles it through a COD Settlement, which creates the Payment Entries.
	"""

	label_key = "payment.cod"
	is_online = False

	def initiate(self, sales_order) -> PaymentResult:
		return PaymentResult(
			status="pending",
			provider=self.code,
			amount=flt(sales_order.rounded_total or sales_order.grand_total),
		)
