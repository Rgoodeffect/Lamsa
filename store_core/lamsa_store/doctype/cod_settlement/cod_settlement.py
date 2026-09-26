# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

"""COD Settlement: the office receives cash from a delivery agent.

On submit, one Payment Entry per delivered order is created (Receive, cash account = this
settlement's Cash Account) and submitted against the order's Sales Invoice. On cancel they are
cancelled and the orders become unsettled again.
"""

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from store_core.services.delivery_flow import update_agent_cash
from store_core.services.orders import system_context


class CODSettlement(Document):
	def validate(self):
		if not self.company or not self.cash_account:
			settings = frappe.get_cached_doc("Lamsa Settings")
			self.company = self.company or settings.company
			self.cash_account = self.cash_account or settings.cod_cash_account
		seen = set()
		total = 0.0
		for row in self.items:
			if row.assignment in seen:
				frappe.throw(_("Row {0}: order {1} is listed twice").format(row.idx, row.order_no))
			seen.add(row.assignment)
			a = frappe.db.get_value(
				"Delivery Assignment",
				row.assignment,
				["agent", "status", "settled", "sales_invoice", "collected_amount", "order_no", "customer"],
				as_dict=True,
			)
			if a.agent != self.agent:
				frappe.throw(_("Row {0}: order {1} belongs to another agent").format(row.idx, a.order_no))
			if a.status != "Delivered" or not a.sales_invoice:
				frappe.throw(
					_("Row {0}: order {1} is not delivered and invoiced").format(row.idx, a.order_no)
				)
			if a.settled and self.docstatus == 0:
				frappe.throw(_("Row {0}: order {1} is already settled").format(row.idx, a.order_no))
			row.order_no, row.sales_invoice, row.customer = a.order_no, a.sales_invoice, a.customer
			row.amount = flt(a.collected_amount)
			total += row.amount
		self.total_amount = total

	def on_submit(self):
		with system_context():
			for row in self.items:
				if flt(row.amount) <= 0:
					continue
				pe = get_payment_entry(
					"Sales Invoice",
					row.sales_invoice,
					party_amount=row.amount,
					bank_account=self.cash_account,
				)
				pe.posting_date = self.posting_date
				pe.reference_no = self.name
				pe.reference_date = self.posting_date
				pe.remarks = _("COD collected by {0} for order {1} ({2})").format(
					self.agent, row.order_no, self.name
				)
				pe.flags.ignore_permissions = True
				pe.insert()
				pe.submit()
				row.db_set("payment_entry", pe.name)
			for row in self.items:
				frappe.db.set_value(
					"Delivery Assignment", row.assignment, {"settled": 1, "settlement": self.name}
				)
		update_agent_cash(self.agent)

	def on_cancel(self):
		with system_context():
			for row in self.items:
				if row.payment_entry:
					pe = frappe.get_doc("Payment Entry", row.payment_entry)
					if pe.docstatus == 1:
						pe.flags.ignore_permissions = True
						pe.cancel()
				frappe.db.set_value("Delivery Assignment", row.assignment, {"settled": 0, "settlement": None})
		update_agent_cash(self.agent)


@frappe.whitelist()
def get_unsettled(agent: str) -> list[dict]:
	"""Delivered orders whose cash this agent still holds (used by the form's Get Orders button)."""
	frappe.has_permission("COD Settlement", "create", throw=True)
	return frappe.get_all(
		"Delivery Assignment",
		filters={"agent": agent, "status": "Delivered", "settled": 0, "sales_invoice": ["is", "set"]},
		fields=["name as assignment", "order_no", "sales_invoice", "customer", "collected_amount as amount"],
		order_by="status_changed_on asc",
	)
