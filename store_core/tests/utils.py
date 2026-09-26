"""Test fixtures built on top of ERPNext's bootstrap test data (_Test Company etc.)."""

import frappe
from erpnext.controllers.item_variant import create_variant
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

from store_core.services import catalog

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"
PRICE_LIST = "Standard Selling"
SIZE = "Lamsa Test Size"
COLOR = "Lamsa Test Color"
ROOT_GROUP = "Lamsa Test Women"
SUB_GROUP = "Lamsa Test Dresses"
GIFTS_GROUP = "Lamsa Test Gifts"
TEMPLATE = "LAMSA-TEST-DRESS"
SIMPLE_ITEM = "LAMSA-TEST-MUG"
GIFT_WRAP = "LAMSA-TEST-GIFT-WRAP"
DELIVERY = "LAMSA-TEST-DELIVERY"
ZONE = "طرابلس-حي الأندلس"


def _ensure(doctype, name, values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


def setup_store(stock_qty: int = 3) -> dict:
	"""Create a small published catalog. Runs inside the test transaction (rolled back after)."""
	_ensure(
		"Item Group",
		ROOT_GROUP,
		{
			"item_group_name": ROOT_GROUP,
			"parent_item_group": "All Item Groups",
			"is_group": 1,
			"lamsa_show_in_store": 1,
			"lamsa_title_ar": "ملابس نسائية",
			"lamsa_slug": "women",
		},
	)
	_ensure(
		"Item Group",
		SUB_GROUP,
		{
			"item_group_name": SUB_GROUP,
			"parent_item_group": ROOT_GROUP,
			"lamsa_show_in_store": 1,
			"lamsa_title_ar": "فساتين",
			"lamsa_slug": "dresses",
		},
	)
	_ensure(
		"Item Group",
		GIFTS_GROUP,
		{
			"item_group_name": GIFTS_GROUP,
			"parent_item_group": "All Item Groups",
			"lamsa_show_in_store": 1,
			"lamsa_title_ar": "هدايا",
			"lamsa_slug": "gifts",
		},
	)
	_ensure(
		"Item Attribute",
		SIZE,
		{
			"attribute_name": SIZE,
			"item_attribute_values": [{"attribute_value": v, "abbr": v} for v in ("S", "M", "L")],
		},
	)
	_ensure(
		"Item Attribute",
		COLOR,
		{
			"attribute_name": COLOR,
			"item_attribute_values": [
				{"attribute_value": "وردي", "abbr": "PNK", "lamsa_swatch": "#D8A7B1"},
				{"attribute_value": "بيج", "abbr": "BGE", "lamsa_swatch": "#E8D9C4"},
			],
		},
	)

	for code, name in ((GIFT_WRAP, "تغليف هدية"), (DELIVERY, "رسوم التوصيل")):
		_ensure(
			"Item",
			code,
			{
				"item_code": code,
				"item_name": name,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
			},
		)
	_price(GIFT_WRAP, 15)

	_ensure(
		"Item",
		TEMPLATE,
		{
			"item_code": TEMPLATE,
			"item_name": "فستان سهرة مطرز",
			"item_group": SUB_GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"has_variants": 1,
			"lamsa_publish": 1,
			"lamsa_featured": 1,
			"attributes": [{"attribute": SIZE}, {"attribute": COLOR}],
		},
	)

	variants = {}
	for size in ("S", "M"):
		for color in ("وردي", "بيج"):
			variant = create_variant(TEMPLATE, {SIZE: size, COLOR: color})
			code = variant.item_code
			if not frappe.db.exists("Item", code):
				variant.insert(ignore_permissions=True)
			variants[(size, color)] = code

	# ERPNext v16 does not allow Item Price on templates: every variant is priced.
	for key, code in variants.items():
		_price(code, 300 if key == ("M", "بيج") else 250)

	_ensure(
		"Item",
		SIMPLE_ITEM,
		{
			"item_code": SIMPLE_ITEM,
			"item_name": "كوب هدية بالأسم",
			"item_group": GIFTS_GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"lamsa_publish": 1,
		},
	)
	_price(SIMPLE_ITEM, 40)

	for code in (variants[("S", "وردي")], variants[("M", "بيج")], SIMPLE_ITEM):
		make_stock_entry(item_code=code, qty=stock_qty, to_warehouse=WAREHOUSE, rate=50, company=COMPANY)

	_ensure(
		"Delivery Zone",
		ZONE,
		{"city": "طرابلس", "area": "حي الأندلس", "fee": 20, "est_days_min": 1, "est_days_max": 2},
	)

	settings = frappe.get_single("Lamsa Settings")
	settings.update(
		{
			"company": COMPANY,
			"selling_price_list": PRICE_LIST,
			"warehouse": WAREHOUSE,
			"customer_group": "_Test Customer Group",
			"territory": "_Test Territory",
			"order_no_prefix": "LT-",
			"max_qty_per_line": 5,
			"size_attribute": SIZE,
			"color_attribute": COLOR,
			"low_stock_threshold": 3,
			"gift_wrap_item": GIFT_WRAP,
			"delivery_fee_item": DELIVERY,
			"gift_message_max_length": 100,
			"default_payment_provider": "cod",
			"enabled_payment_providers": "cod",
			"notification_channel": "log",
			"whatsapp_number": "0912345678",
		}
	)
	settings.save(ignore_permissions=True)
	frappe.clear_document_cache("Lamsa Settings", "Lamsa Settings")
	catalog.invalidate_index()
	return {"variants": variants}


def _price(item_code, rate):
	if not frappe.db.exists("Item Price", {"item_code": item_code, "price_list": PRICE_LIST}):
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": PRICE_LIST,
				"price_list_rate": rate,
			}
		).insert(ignore_permissions=True)


API_USER = "lamsa-test-api@example.com"


def api_user() -> str:
	"""A user with only the storefront API role, like the real storefront credentials."""
	if not frappe.db.exists("User", API_USER):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": API_USER,
				"first_name": "Lamsa API Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Lamsa Storefront API"}],
			}
		).insert(ignore_permissions=True)
	return API_USER
