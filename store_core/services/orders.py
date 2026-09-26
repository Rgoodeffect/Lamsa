"""Quote, checkout and tracking.

Server-side rules (never trust the browser):
- The cart sends only item codes and quantities.
- Item prices, pricing rules and discounts come from ERPNext's own Sales Order logic.
- Gift wrap fee = rate of the gift-wrap service item in the store's selling price list.
- Delivery fee = Delivery Zone.fee.
The same `build_sales_order` is used for the quote and for the real order, so they match.
"""

import hmac
import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import add_days, cint, flt, nowdate, strip_html

from store_core.providers.payments import registry as payment_registry
from store_core.services import catalog
from store_core.services.customer import get_or_create_address, get_or_create_customer, get_primary_contact
from store_core.services.settings import get_settings
from store_core.utils import status_machine as sm
from store_core.utils.phone import InvalidPhone, normalize_libyan_phone

MAX_LINES = 30
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@contextmanager
def system_context():
	"""Run ERPNext's selling logic with full permissions, then restore the caller.

	ERPNext's pricing code (get_item_details) checks Item/Price List read permission for the
	session user. The storefront API user deliberately has no desk permissions, and adding
	Custom DocPerms would replace the standard permissions of those core DocTypes. Endpoints
	verify the "Lamsa Storefront API" role before any call reaches this context, and inputs are
	validated first; documents record the storefront as their source (lamsa_source).
	"""
	user = frappe.session.user
	if user == "Administrator":
		yield
		return
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(user)


class CheckoutError(frappe.ValidationError):
	"""Validation error whose `code` the storefront maps to an Arabic message."""

	def __init__(self, code: str, message: str | None = None, **details):
		super().__init__(message or code)
		self.code = code
		self.details = details


# ---------------------------------------------------------------------------
# Cart validation
# ---------------------------------------------------------------------------


def validate_cart(items: list[dict], fresh_stock: bool = False) -> list[dict]:
	"""Merge duplicate lines and check every item is published, priced and in stock.

	fresh_stock=True reads Bin directly (used at checkout after the rows are locked) instead of
	the cached catalog index.
	"""
	if not isinstance(items, list) or not items:
		raise CheckoutError("cart_empty")
	if len(items) > MAX_LINES:
		raise CheckoutError("cart_too_large")

	settings = get_settings()
	max_qty = cint(settings.max_qty_per_line) or 10

	merged: dict[str, int] = {}
	for row in items:
		if not isinstance(row, dict):
			raise CheckoutError("invalid_item")
		code = str(row.get("item_code") or "").strip()
		qty = cint(row.get("qty"))
		if not code or qty < 1:
			raise CheckoutError("invalid_item", item_code=code)
		merged[code] = merged.get(code, 0) + qty

	index = catalog.get_index()
	stock = catalog.load_stock(list(merged), settings.warehouse) if fresh_stock else None
	lines = []
	for code, qty in merged.items():
		product, variant = catalog.find_sellable(index, code)
		if not product:
			raise CheckoutError("item_unavailable", item_code=code)
		if product["has_variants"] and not variant:
			raise CheckoutError("variant_required", item_code=code)
		sellable = variant or product
		if stock is not None:
			available = catalog.available_qty(stock, code, sellable["is_stock_item"])
		else:
			available = sellable["available"]
		if qty > max_qty:
			raise CheckoutError("qty_limit", item_code=code, max_qty=max_qty)
		if qty > available:
			raise CheckoutError("out_of_stock", item_code=code, available=int(max(available, 0)))
		lines.append({"item_code": code, "qty": qty, "product": product, "variant": variant})
	return lines


def get_zone(zone_name: str | None) -> dict | None:
	if not zone_name:
		return None
	zone = frappe.db.get_value(
		"Delivery Zone",
		{"name": zone_name, "enabled": 1},
		["name", "city", "area", "fee", "est_days_min", "est_days_max"],
		as_dict=True,
	)
	if not zone:
		raise CheckoutError("invalid_zone")
	return zone


# ---------------------------------------------------------------------------
# Sales Order builder (shared by quote and checkout)
# ---------------------------------------------------------------------------


def build_sales_order(lines: list[dict], zone: dict | None, gift_wrap: bool, customer: str | None = None):
	settings = get_settings()
	so = frappe.new_doc("Sales Order")
	so.company = settings.company
	so.customer = customer
	so.order_type = "Sales"
	so.transaction_date = nowdate()
	so.delivery_date = add_days(nowdate(), cint(zone.est_days_max) if zone else 3)
	so.selling_price_list = settings.selling_price_list
	so.currency = settings.currency
	so.set_warehouse = settings.warehouse
	so.ignore_pricing_rule = 0

	for line in lines:
		so.append(
			"items",
			{
				"item_code": line["item_code"],
				"qty": line["qty"],
				"warehouse": settings.warehouse,
				"delivery_date": so.delivery_date,
			},
		)

	if gift_wrap:
		# Rate comes from the price list via set_missing_values.
		so.append(
			"items",
			{"item_code": settings.gift_wrap_item, "qty": 1, "delivery_date": so.delivery_date},
		)

	if zone:
		fee = flt(zone.fee)
		so.append(
			"items",
			{
				"item_code": settings.delivery_fee_item,
				"qty": 1,
				"delivery_date": so.delivery_date,
				# set before set_missing_values so ERPNext keeps the zone fee
				"price_list_rate": fee,
				"rate": fee,
				"discount_percentage": 0,
			},
		)

	so.flags.ignore_permissions = True
	so.set_missing_values()
	_enforce_service_rates(so, settings, zone)
	so.calculate_taxes_and_totals()
	return so


def _enforce_service_rates(so, settings, zone):
	"""Delivery fee must equal the zone fee even if a price or pricing rule exists for the item."""
	for item in so.items:
		if zone and item.item_code == settings.delivery_fee_item:
			fee = flt(zone.fee)
			item.price_list_rate = fee
			item.rate = fee
			item.discount_percentage = 0
			item.discount_amount = 0
			item.margin_rate_or_amount = 0
			item.pricing_rules = ""


def summarize(so, lines: list[dict], zone: dict | None) -> dict:
	settings = get_settings()
	by_code = {line["item_code"]: line for line in lines}
	out_items, subtotal, gift_wrap_fee, delivery_fee = [], 0.0, 0.0, 0.0
	for item in so.items:
		if item.item_code == settings.gift_wrap_item:
			gift_wrap_fee += flt(item.amount)
			continue
		if item.item_code == settings.delivery_fee_item:
			delivery_fee += flt(item.amount)
			continue
		line = by_code.get(item.item_code)
		product, variant = (line["product"], line["variant"]) if line else ({}, None)
		subtotal += flt(item.amount)
		out_items.append(
			{
				"item_code": item.item_code,
				"name": product.get("name") or item.item_name,
				"slug": product.get("slug"),
				"image": (variant or {}).get("image") or product.get("image"),
				"attributes": (variant or {}).get("attributes", {}),
				"qty": flt(item.qty),
				"price_list_rate": flt(item.price_list_rate),
				"rate": flt(item.rate),
				"amount": flt(item.amount),
			}
		)

	return {
		"currency": so.currency,
		"items": out_items,
		"subtotal": flt(subtotal, 2),
		"gift_wrap_fee": flt(gift_wrap_fee, 2),
		"delivery_fee": flt(delivery_fee, 2),
		"discount": flt(so.discount_amount, 2),
		"taxes": flt(so.total_taxes_and_charges, 2),
		"grand_total": flt(so.rounded_total or so.grand_total, 2),
		"zone": _zone_public(zone),
	}


def _zone_public(zone):
	if not zone:
		return None
	return {
		"name": zone.name,
		"city": zone.city,
		"area": zone.area,
		"fee": flt(zone.fee),
		"est_days_min": cint(zone.est_days_min),
		"est_days_max": cint(zone.est_days_max),
	}


def quote(items: list[dict], zone: str | None = None, gift_wrap: bool = False) -> dict:
	lines = validate_cart(items)
	zone_doc = get_zone(zone)
	with system_context():
		so = build_sales_order(lines, zone_doc, bool(cint(gift_wrap)))
		return summarize(so, lines, zone_doc)


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


def validate_customer_input(data: dict) -> dict:
	settings = get_settings()
	name = strip_html(str(data.get("full_name") or "")).strip()
	if len(name) < 2 or len(name) > 140:
		raise CheckoutError("invalid_name")
	try:
		phone = normalize_libyan_phone(data.get("phone"))
	except InvalidPhone:
		raise CheckoutError("invalid_phone")

	notes = strip_html(str(data.get("address_notes") or "")).strip()
	if len(notes) > 500:
		raise CheckoutError("address_notes_too_long")

	gift_wrap = bool(cint(data.get("gift_wrap")))
	gift_message = strip_html(str(data.get("gift_message") or "")).strip() if gift_wrap else ""
	if len(gift_message) > (cint(settings.gift_message_max_length) or 250):
		raise CheckoutError("gift_message_too_long")

	event_id = str(data.get("event_id") or "")
	if not EVENT_ID_RE.match(event_id):
		raise CheckoutError("invalid_event_id")

	provider = str(data.get("payment_provider") or settings.default_payment_provider or "cod")
	if provider not in payment_registry.enabled_codes():
		raise CheckoutError("payment_unavailable")

	if not data.get("zone"):
		raise CheckoutError("invalid_zone")

	return {
		"full_name": name,
		"phone": phone,
		"address_notes": notes,
		"gift_wrap": gift_wrap,
		"gift_message": gift_message,
		"event_id": event_id,
		"payment_provider": provider,
		"zone": str(data["zone"]),
		"source": data.get("source") if data.get("source") in ("Storefront", "WhatsApp") else "Storefront",
	}


def place_order(data: dict) -> dict:
	clean = validate_customer_input(data)
	with system_context():
		return _place_order(clean, data)


def _place_order(clean: dict, data: dict) -> dict:

	# Idempotency: the storefront generates one event_id per checkout attempt (also used as the
	# Meta Pixel/CAPI dedup id). A retried request returns the order that was already created.
	existing = frappe.db.get_value("Sales Order", {"lamsa_event_id": clean["event_id"]}, "name")
	if existing:
		return order_response(frappe.get_doc("Sales Order", existing), duplicate=True)

	zone = get_zone(clean["zone"])
	_lock_stock([row.get("item_code") for row in data.get("items") or [] if isinstance(row, dict)])
	lines = validate_cart(data.get("items"), fresh_stock=True)

	settings = get_settings()
	customer = get_or_create_customer(clean["full_name"], clean["phone"])
	address = get_or_create_address(
		customer, clean["full_name"], clean["phone"], zone.city, zone.area, clean["address_notes"]
	)

	so = build_sales_order(lines, zone, clean["gift_wrap"], customer=customer)
	so.customer_address = address
	so.shipping_address_name = address
	so.contact_person = get_primary_contact(customer)
	so.lamsa_order_no = make_autoname(f"{settings.order_no_prefix or 'L-'}.#####")
	so.lamsa_source = clean["source"]
	so.lamsa_status = sm.NEW
	so.lamsa_phone = clean["phone"]
	so.lamsa_delivery_zone = zone.name
	so.lamsa_address_notes = clean["address_notes"]
	so.lamsa_gift_wrap = 1 if clean["gift_wrap"] else 0
	so.lamsa_gift_message = clean["gift_message"]
	so.lamsa_payment_provider = clean["payment_provider"]
	so.lamsa_event_id = clean["event_id"]
	so.flags.ignore_permissions = True
	so.insert()  # Draft: staff confirm by phone, then "Confirmed" submits it.

	assignment = frappe.get_doc(
		{
			"doctype": "Delivery Assignment",
			"sales_order": so.name,
			"order_no": so.lamsa_order_no,
			"status": sm.NEW,
			"zone": zone.name,
			"customer": customer,
			"customer_name": clean["full_name"],
			"phone": clean["phone"],
			"address": "\n".join(filter(None, [f"{zone.city} - {zone.area}", clean["address_notes"]])),
			"gift_wrap": so.lamsa_gift_wrap,
			"gift_message": so.lamsa_gift_message,
			"payment_provider": clean["payment_provider"],
			"expected_amount": flt(so.rounded_total or so.grand_total),
		}
	)
	assignment.flags.ignore_permissions = True
	assignment.insert()

	payment = payment_registry.get_provider(clean["payment_provider"]).initiate(so)

	frappe.enqueue(
		"store_core.services.events.order_placed",
		queue="short",
		enqueue_after_commit=True,
		sales_order=so.name,
	)

	return order_response(so, payment=payment.as_dict())


def _lock_stock(item_codes: list[str]):
	"""Serialize concurrent checkouts for the same items (SELECT ... FOR UPDATE on Bin)."""
	codes = sorted({str(c) for c in item_codes if c})
	if not codes:
		return
	warehouse = get_settings().warehouse
	frappe.db.sql(
		"select name from `tabBin` where warehouse=%s and item_code in %s for update",
		(warehouse, tuple(codes)),
	)


def order_response(so, payment: dict | None = None, duplicate: bool = False) -> dict:
	settings = get_settings()
	items = [
		{
			"item_code": i.item_code,
			"name": i.item_name,
			"qty": flt(i.qty),
			"rate": flt(i.rate),
			"amount": flt(i.amount),
		}
		for i in so.items
		if i.item_code not in (settings.gift_wrap_item, settings.delivery_fee_item)
	]
	zone = get_zone_safe(so.lamsa_delivery_zone)
	return {
		"order_no": so.lamsa_order_no,
		"status": so.lamsa_status,
		"currency": so.currency,
		"grand_total": flt(so.rounded_total or so.grand_total, 2),
		"items": items,
		"zone": _zone_public(zone),
		"payment_provider": so.lamsa_payment_provider,
		"payment": payment or {"status": "pending"},
		"event_id": so.lamsa_event_id,
		"duplicate": duplicate,
	}


def get_zone_safe(name):
	if not name:
		return None
	return frappe.db.get_value(
		"Delivery Zone", name, ["name", "city", "area", "fee", "est_days_min", "est_days_max"], as_dict=True
	)


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------


def track_order(order_no: str, phone: str) -> dict:
	"""Same error for 'no such order' and 'wrong phone' so order numbers cannot be probed."""
	not_found = CheckoutError("order_not_found")
	order_no = str(order_no or "").strip().upper()
	try:
		phone = normalize_libyan_phone(phone)
	except InvalidPhone:
		raise not_found
	if not order_no or len(order_no) > 30:
		raise not_found

	row = frappe.db.get_value(
		"Sales Order", {"lamsa_order_no": order_no}, ["name", "lamsa_phone", "docstatus"], as_dict=True
	)
	if not row or not hmac.compare_digest((row.lamsa_phone or "").encode(), phone.encode()):
		raise not_found

	so = frappe.get_doc("Sales Order", row.name)
	assignment = frappe.db.get_value(
		"Delivery Assignment",
		{"sales_order": so.name},
		["status", "status_changed_on", "modified"],
		as_dict=True,
	)
	status = (assignment and assignment.status) or so.lamsa_status or sm.NEW
	response = order_response(so)
	response.update(
		{
			"status": status,
			"steps": list(sm.TRACKING_STEPS),
			"step_index": sm.TRACKING_STEPS.index(status) if status in sm.TRACKING_STEPS else -1,
			"placed_on": str(so.creation),
			"updated_on": str(
				(assignment and (assignment.status_changed_on or assignment.modified)) or so.modified
			),
			"gift_wrap": cint(so.lamsa_gift_wrap),
		}
	)
	response.pop("event_id", None)
	response.pop("payment", None)
	return response
