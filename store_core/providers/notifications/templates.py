"""Arabic order-status message texts.

Customer-facing, so they live in one place. With WhatsApp Business Cloud API these texts must also
be registered as approved message templates (same names) in Meta Business Manager.
"""

TEMPLATES = {
	"order_placed": "أهلاً {customer_name} 🌸\nاستلمنا طلبك رقم {order_no} بقيمة {grand_total} {currency}.\nسنتواصل معك قريباً لتأكيد الطلب.\nلمسة",
	"order_confirmed": "تم تأكيد طلبك رقم {order_no} ✅\nموعد التوصيل المتوقع خلال {eta}.\nلمسة",
	"out_for_delivery": "طلبك رقم {order_no} في الطريق إليك 🚚\nالمبلغ المطلوب عند الاستلام: {grand_total} {currency}.",
	"delivered": "تم توصيل طلبك رقم {order_no}. شكراً لاختيارك لمسة 💕",
	"returned": "تم إرجاع طلبك رقم {order_no}. للاستفسار تواصل معنا عبر واتساب.",
	"cancelled": "تم إلغاء طلبك رقم {order_no}. للاستفسار تواصل معنا عبر واتساب.",
	"coupon_earned": "مبروك {customer_name} 🎁\nلأن قيمة طلبك وصلت للمبلغ المطلوب، ربحتِ كوبون خصم {coupon_percent}% على طلبك القادم.\nكود الكوبون: {coupon_code}\nصالح حتى {coupon_valid_upto}.\nلمسة",
}


# Delivery Assignment status -> template. Lives here, next to the texts, so it can be unit tested
# without a bench; `services.events` reads it.
STATUS_TEMPLATES = {
	"Confirmed": "order_confirmed",
	"Out for Delivery": "out_for_delivery",
	"Delivered": "delivered",
	"Returned": "returned",
	"Cancelled": "cancelled",
}


def render(template: str, context: dict) -> str:
	text = TEMPLATES.get(template)
	if not text:
		return ""
	try:
		return text.format(**context)
	except (KeyError, IndexError):
		return text
