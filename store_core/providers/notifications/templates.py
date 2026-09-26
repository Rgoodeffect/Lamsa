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
}


def render(template: str, context: dict) -> str:
	text = TEMPLATES.get(template)
	if not text:
		return ""
	try:
		return text.format(**context)
	except KeyError, IndexError:
		return text
