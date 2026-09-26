"""Loyalty coupons: earn one on a delivered order, spend it on the next.

The coupon itself is ERPNext's **Coupon Code**, so ERPNext owns its lifecycle: `Sales Order.validate`
calls `validate_coupon_code` (dates, maximum use) and `on_submit` / `on_cancel` move the `used`
counter, which is what stops a coupon being spent twice or staying burnt after a cancellation.

The *discount* is applied as the Sales Order's own `discount_amount` on the grand total, not through a
Pricing Rule. A coupon-based Pricing Rule looks like the obvious fit but would not work here:
transaction-level rules are applied by ERPNext's client-side code (`transaction.js` / POS), never on a
server-side save, so the cart quote and the order — both built by `services.orders.build_sales_order`
— would silently ignore it. `discount_amount` is core arithmetic inside `calculate_taxes_and_totals`
and behaves identically in both.

The discount is a percentage of the **goods** only: the delivery fee and gift wrap are passed through
at cost, so a coupon does not eat into them.

Coupons are earned on **Delivered**, not at checkout: a cancelled order must not mint one.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate, random_string

from store_core.services.orders import CheckoutError
from store_core.services.settings import get_settings

CODE_PREFIX = "LAMSA"
CODE_LENGTH = 6
#: The coupon's own percentage, kept on the document so a later settings change cannot silently
#: re-price a coupon a customer is already holding.
PERCENT_FIELD = "lamsa_discount_percent"


# ---------------------------------------------------------------------------
# Spending a coupon
# ---------------------------------------------------------------------------


def resolve(code: str | None) -> dict | None:
	"""Customer-typed code -> {"name", "percent"}, or None when nothing was typed.

	`Sales Order.coupon_code` is a Link and holds the document name, while the customer knows the
	`coupon_code` string; this is the mapping between the two.
	"""
	code = str(code or "").strip().upper()
	if not code:
		return None
	if len(code) > 40:
		raise CheckoutError("invalid_coupon")
	row = frappe.db.get_value(
		"Coupon Code",
		{"coupon_code": code},
		["name", "valid_from", "valid_upto", "maximum_use", "used", PERCENT_FIELD],
		as_dict=True,
	)
	if not row:
		raise CheckoutError("invalid_coupon")

	today = getdate(nowdate())
	if row.valid_from and getdate(row.valid_from) > today:
		raise CheckoutError("coupon_not_started")
	if row.valid_upto and getdate(row.valid_upto) < today:
		raise CheckoutError("coupon_expired")
	if cint(row.maximum_use) and cint(row.used) >= cint(row.maximum_use):
		raise CheckoutError("coupon_used")

	percent = flt(row.get(PERCENT_FIELD))
	if percent <= 0:
		raise CheckoutError("invalid_coupon")
	return {"name": row.name, "code": code, "percent": percent, "valid_upto": str(row.valid_upto or "")}


def discount_for(goods_total: float, coupon: dict | None) -> float:
	"""The coupon's value against this order's goods, rounded to 2 decimals."""
	if not coupon:
		return 0.0
	return flt(flt(goods_total) * flt(coupon["percent"]) / 100, 2)


def public_info(coupon: dict | None, discount: float = 0.0) -> dict | None:
	"""What the storefront may show about an applied coupon."""
	if not coupon:
		return None
	return {
		"code": coupon["code"],
		"percent": flt(coupon["percent"]),
		"discount": flt(discount, 2),
		"valid_upto": coupon.get("valid_upto") or "",
	}


# ---------------------------------------------------------------------------
# Earning a coupon
# ---------------------------------------------------------------------------


def grant_reward(so) -> dict | None:
	"""Create a coupon for this customer when the delivered order reaches the threshold.

	Returns the new coupon's public info, or None when nothing was earned. Never raises: a promotion
	must not be able to break a delivery.
	"""
	try:
		settings = get_settings()
		if not cint(settings.coupon_reward_enabled):
			return None
		threshold = flt(settings.coupon_reward_threshold)
		percent = flt(settings.coupon_reward_percent)
		if threshold <= 0 or percent <= 0:
			return None
		if flt(so.rounded_total or so.grand_total) < threshold:
			return None
		if frappe.db.exists("Coupon Code", {"coupon_name": _coupon_name(so)}):
			return None  # one coupon per order, however often a status change is replayed
		return _create_coupon(so, settings, percent)
	except Exception:
		frappe.log_error(title=f"Lamsa: could not grant a coupon for {so.name}")
		return None


def _coupon_name(so) -> str:
	return f"Lamsa Reward {so.lamsa_order_no or so.name}"


def _create_coupon(so, settings, percent: float) -> dict:
	days = cint(settings.coupon_reward_validity_days) or 30
	valid_upto = add_days(nowdate(), days)
	coupon = frappe.get_doc(
		{
			"doctype": "Coupon Code",
			"coupon_name": _coupon_name(so),
			# "Gift Card" is ERPNext's single-use, customer-bound coupon: exactly a personal reward.
			"coupon_type": "Gift Card",
			"customer": so.customer,
			"coupon_code": _unique_code(),
			"valid_from": nowdate(),
			"valid_upto": valid_upto,
			"maximum_use": 1,
			PERCENT_FIELD: percent,
			"description": _("Thank-you coupon for order {0}").format(so.lamsa_order_no or so.name),
		}
	)
	coupon.flags.ignore_permissions = True
	coupon.insert()
	return {
		"code": coupon.coupon_code,
		"percent": percent,
		"discount": 0.0,
		"valid_upto": str(valid_upto),
	}


def _unique_code() -> str:
	for _attempt in range(10):
		code = f"{CODE_PREFIX}{random_string(CODE_LENGTH).upper()}"
		if not frappe.db.exists("Coupon Code", {"coupon_code": code}):
			return code
	frappe.throw(_("Could not generate a unique coupon code"))
