"""Integration tests: catalog, quote, checkout and tracking against a real ERPNext site.

Run: bench --site <test-site> run-tests --app store_core
"""

import frappe
from erpnext.tests.utils import ERPNextTestSuite

from store_core.services import catalog, orders
from store_core.tests import utils as t
from store_core.utils import status_machine as sm


class TestStoreOrders(ERPNextTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.data = t.setup_store(stock_qty=3)
		self.pink_s = self.data["variants"][("S", "وردي")]
		self.beige_m = self.data["variants"][("M", "بيج")]

	def tearDown(self):
		catalog.invalidate_index()
		super().tearDown()

	def checkout_payload(self, **overrides):
		payload = {
			"items": [{"item_code": self.pink_s, "qty": 1}],
			"full_name": "سارة محمد",
			"phone": "091 234 5678",
			"zone": t.ZONE,
			"event_id": frappe.generate_hash(length=20),
			"address_notes": "بجانب مسجد الأندلس",
			"gift_wrap": 0,
			"payment_provider": "cod",
		}
		payload.update(overrides)
		return payload

	# -- catalog ---------------------------------------------------------------

	def test_index_prices_stock_and_filters(self):
		index = catalog.get_index()
		dress = catalog.find_product(index, "فستان-سهرة-مطرز")
		self.assertIsNotNone(dress)
		self.assertEqual(dress["min_price"], 250)
		self.assertEqual(dress["max_price"], 300)
		self.assertEqual(dress["sizes"], ["S", "M"])
		self.assertEqual({c["name"] for c in dress["colors"]}, {"وردي", "بيج"})
		self.assertEqual(
			{c["name"]: c["swatch"] for c in dress["colors"]}, {"وردي": "#D8A7B1", "بيج": "#E8D9C4"}
		)

		# parent category includes the sub-category
		self.assertIn(dress["code"], [p["code"] for p in catalog.filter_products(index, category="women")])
		# size+colour filter that only matches an out-of-stock variant
		out = catalog.filter_products(index, sizes=["M"], colors=["وردي"], in_stock=True)
		self.assertNotIn(dress["code"], [p["code"] for p in out])
		self.assertIn(
			dress["code"],
			[p["code"] for p in catalog.filter_products(index, sizes=["M"], colors=["بيج"], in_stock=True)],
		)
		# price filter
		self.assertNotIn(t.SIMPLE_ITEM, [p["code"] for p in catalog.filter_products(index, min_price=100)])

	def test_arabic_search_normalization(self):
		index = catalog.get_index()
		# "مطرّز" with shadda and alef variants still matches "مطرز"
		found = catalog.filter_products(index, query="فستان مطرّز")
		self.assertEqual([p["code"] for p in found], [t.TEMPLATE])
		self.assertEqual(catalog.filter_products(index, query="غير موجود"), [])

	# -- quote -----------------------------------------------------------------

	def test_quote_uses_server_prices_and_fees(self):
		result = orders.quote(
			[{"item_code": self.pink_s, "qty": 2, "rate": 1}, {"item_code": self.beige_m, "qty": 1}],
			zone=t.ZONE,
			gift_wrap=True,
		)
		self.assertEqual(result["subtotal"], 2 * 250 + 300)
		self.assertEqual(result["gift_wrap_fee"], 15)
		self.assertEqual(result["delivery_fee"], 20)
		self.assertEqual(result["grand_total"], 800 + 15 + 20)

	def test_quote_rejects_bad_carts(self):
		with self.assertRaises(orders.CheckoutError) as ctx:
			orders.quote([{"item_code": t.TEMPLATE, "qty": 1}])
		self.assertEqual(ctx.exception.code, "item_unavailable")

		with self.assertRaises(orders.CheckoutError) as ctx:
			orders.quote([{"item_code": self.pink_s, "qty": 4}])
		self.assertEqual(ctx.exception.code, "out_of_stock")

		with self.assertRaises(orders.CheckoutError) as ctx:
			orders.quote([{"item_code": self.pink_s, "qty": 1}], zone="nowhere")
		self.assertEqual(ctx.exception.code, "invalid_zone")

	# -- checkout ----------------------------------------------------------------

	def test_place_order_creates_customer_draft_order_and_assignment(self):
		result = orders.place_order(self.checkout_payload(gift_wrap=1, gift_message="كل عام وأنتِ بخير"))
		self.assertTrue(result["order_no"].startswith("LT-"))
		self.assertEqual(result["grand_total"], 250 + 15 + 20)
		self.assertEqual(result["payment"]["status"], "pending")

		so = frappe.get_doc("Sales Order", {"lamsa_order_no": result["order_no"]})
		self.assertEqual(so.docstatus, 0)
		self.assertEqual(so.lamsa_phone, "+218912345678")
		self.assertEqual(so.lamsa_status, sm.NEW)
		self.assertEqual(so.lamsa_gift_message, "كل عام وأنتِ بخير")
		self.assertEqual(frappe.db.get_value("Customer", so.customer, "lamsa_phone"), "+218912345678")

		assignment = frappe.get_doc("Delivery Assignment", {"sales_order": so.name})
		self.assertEqual(assignment.status, sm.NEW)
		self.assertEqual(assignment.expected_amount, 285)

		# the same phone in another format reuses the customer
		second = orders.place_order(
			self.checkout_payload(phone="+218 91 234 5678", items=[{"item_code": t.SIMPLE_ITEM, "qty": 1}])
		)
		so2 = frappe.get_doc("Sales Order", {"lamsa_order_no": second["order_no"]})
		self.assertEqual(so2.customer, so.customer)

	def test_place_order_is_idempotent(self):
		payload = self.checkout_payload()
		first = orders.place_order(payload)
		again = orders.place_order(payload)
		self.assertEqual(first["order_no"], again["order_no"])
		self.assertTrue(again["duplicate"])
		self.assertEqual(frappe.db.count("Sales Order", {"lamsa_event_id": payload["event_id"]}), 1)

	def test_draft_orders_hold_stock(self):
		orders.place_order(self.checkout_payload(items=[{"item_code": self.pink_s, "qty": 2}]))
		with self.assertRaises(orders.CheckoutError) as ctx:
			orders.place_order(self.checkout_payload(items=[{"item_code": self.pink_s, "qty": 2}]))
		self.assertEqual(ctx.exception.code, "out_of_stock")
		self.assertEqual(ctx.exception.details.get("available"), 1)

	def test_place_order_validates_input(self):
		cases = {
			"invalid_phone": {"phone": "021 333 4444"},
			"invalid_name": {"full_name": "x"},
			"invalid_zone": {"zone": ""},
			"gift_message_too_long": {"gift_wrap": 1, "gift_message": "ا" * 101},
			"payment_unavailable": {"payment_provider": "moamalat"},
			"invalid_event_id": {"event_id": "bad id!"},
		}
		for code, override in cases.items():
			with self.subTest(code=code):
				with self.assertRaises(orders.CheckoutError) as ctx:
					orders.place_order(self.checkout_payload(**override))
				self.assertEqual(ctx.exception.code, code)

	# -- tracking ----------------------------------------------------------------

	def test_track_order_requires_matching_phone(self):
		result = orders.place_order(self.checkout_payload())
		tracked = orders.track_order(result["order_no"].lower(), "00218912345678")
		self.assertEqual(tracked["status"], sm.NEW)
		self.assertEqual(tracked["step_index"], 0)
		self.assertNotIn("event_id", tracked)

		for phone in ("0922222222", "garbage"):
			with self.assertRaises(orders.CheckoutError) as ctx:
				orders.track_order(result["order_no"], phone)
			self.assertEqual(ctx.exception.code, "order_not_found")
