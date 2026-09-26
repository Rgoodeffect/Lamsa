"""Integration tests: delivery status flow, agent API and COD settlement."""

import frappe
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import flt

from store_core.api.v1 import agent as agent_api
from store_core.services import catalog, orders
from store_core.tests import utils as t
from store_core.utils import status_machine as sm

AGENT_USER = "lamsa-agent@example.com"
OTHER_AGENT_USER = "lamsa-agent-2@example.com"


def _agent(name: str, user: str) -> str:
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": name,
				"send_welcome_email": 0,
				"roles": [{"role": "Lamsa Delivery Agent"}],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Delivery Agent", name):
		frappe.get_doc(
			{"doctype": "Delivery Agent", "agent_name": name, "phone": "0925555555", "user": user}
		).insert(ignore_permissions=True)
	return name


class TestDeliveryFlow(ERPNextTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		data = t.setup_store(stock_qty=3)
		self.item = data["variants"][("S", "وردي")]
		cash = frappe.db.get_value(
			"Account", {"company": t.COMPANY, "account_type": "Cash", "is_group": 0}, "name"
		)
		frappe.db.set_single_value("Lamsa Settings", "cod_cash_account", cash)
		frappe.clear_document_cache("Lamsa Settings", "Lamsa Settings")
		self.agent = _agent("مندوب اختبار", AGENT_USER)
		self.other_agent = _agent("مندوب آخر", OTHER_AGENT_USER)

		frappe.set_user(t.api_user())
		result = orders.place_order(
			{
				"items": [{"item_code": self.item, "qty": 1}],
				"full_name": "هند علي",
				"phone": "0931234567",
				"zone": t.ZONE,
				"event_id": frappe.generate_hash(length=20),
				"gift_wrap": 1,
				"gift_message": "مبروك",
				"payment_provider": "cod",
			}
		)
		frappe.set_user("Administrator")
		self.so_name = frappe.db.get_value("Sales Order", {"lamsa_order_no": result["order_no"]}, "name")
		self.assignment = frappe.get_doc("Delivery Assignment", {"sales_order": self.so_name})

	def tearDown(self):
		frappe.set_user("Administrator")
		catalog.invalidate_index()
		super().tearDown()

	def set_status(self, status, **values):
		doc = frappe.get_doc("Delivery Assignment", self.assignment.name)
		doc.update({"status": status, **values})
		doc.save()
		return doc

	def stock(self):
		return flt(
			frappe.db.get_value("Bin", {"item_code": self.item, "warehouse": t.WAREHOUSE}, "actual_qty")
		)

	def test_full_cod_cycle_and_settlement(self):
		self.set_status(sm.CONFIRMED)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "lamsa_status"), sm.CONFIRMED)

		stock_before = self.stock()
		doc = self.set_status(sm.OUT_FOR_DELIVERY, agent=self.agent)
		self.assertTrue(doc.delivery_note)
		self.assertEqual(self.stock(), stock_before - 1)
		dn = frappe.get_doc("Delivery Note", doc.delivery_note)
		self.assertEqual(dn.lamsa_gift_message, "مبروك")
		self.assertEqual(dn.lamsa_order_no, doc.order_no)
		html = frappe.get_print("Delivery Note", dn.name, print_format="Lamsa Delivery Note")
		self.assertIn("مبروك", html)

		# the agent marks it delivered from the /agent page API
		frappe.set_user(AGENT_USER)
		res = agent_api.update_status(doc.name, sm.DELIVERED, collected_amount=str(doc.expected_amount))
		self.assertTrue(res["ok"])
		frappe.set_user("Administrator")

		doc.reload()
		self.assertEqual(doc.status, sm.DELIVERED)
		si = frappe.get_doc("Sales Invoice", doc.sales_invoice)
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(flt(si.outstanding_amount), flt(doc.expected_amount))
		self.assertEqual(
			flt(frappe.db.get_value("Delivery Agent", self.agent, "cash_in_hand")), flt(doc.expected_amount)
		)

		settlement = frappe.get_doc(
			{
				"doctype": "COD Settlement",
				"agent": self.agent,
				"posting_date": frappe.utils.today(),
				"items": [{"assignment": doc.name}],
			}
		)
		settlement.insert()
		self.assertEqual(flt(settlement.total_amount), flt(doc.expected_amount))
		settlement.submit()
		self.assertEqual(flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")), 0)
		self.assertEqual(frappe.db.get_value("Delivery Assignment", doc.name, "settled"), 1)
		self.assertEqual(flt(frappe.db.get_value("Delivery Agent", self.agent, "cash_in_hand")), 0)

		settlement.cancel()
		self.assertEqual(
			flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")), flt(doc.expected_amount)
		)
		self.assertEqual(frappe.db.get_value("Delivery Assignment", doc.name, "settled"), 0)

	def test_return_restores_stock(self):
		self.set_status(sm.CONFIRMED)
		stock_before = self.stock()
		self.set_status(sm.OUT_FOR_DELIVERY, agent=self.agent)
		doc = self.set_status(sm.RETURNED)
		self.assertTrue(doc.return_note)
		self.assertEqual(self.stock(), stock_before)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "status"), "Closed")

	def test_cancel_draft_and_confirmed(self):
		doc = self.set_status(sm.CANCELLED)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "docstatus"), 0)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "lamsa_status"), sm.CANCELLED)
		self.assertEqual(doc.status, sm.CANCELLED)

	def test_cancel_confirmed_order_cancels_sales_order(self):
		self.set_status(sm.CONFIRMED)
		self.set_status(sm.CANCELLED)
		self.assertEqual(frappe.db.get_value("Sales Order", self.so_name, "docstatus"), 2)

	def test_invalid_transitions_and_agent_rules(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_status(sm.DELIVERED)
		self.set_status(sm.CONFIRMED)
		with self.assertRaises(frappe.ValidationError):
			self.set_status(sm.OUT_FOR_DELIVERY)  # no agent

		doc = self.set_status(sm.OUT_FOR_DELIVERY, agent=self.agent)
		frappe.set_user(OTHER_AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			agent_api.update_status(doc.name, sm.DELIVERED)
		frappe.set_user(AGENT_USER)
		res = agent_api.update_status(doc.name, sm.CANCELLED)
		self.assertFalse(res["ok"])
		frappe.set_user(t.api_user())
		with self.assertRaises(frappe.PermissionError):
			agent_api.update_status(doc.name, sm.DELIVERED)
