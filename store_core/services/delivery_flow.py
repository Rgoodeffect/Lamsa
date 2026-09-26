"""Side effects of Delivery Assignment status changes (called from its controller).

New -> Confirmed           submit the Sales Order (reserves stock in ERPNext)
Confirmed -> Out for Del.  create + submit the Delivery Note (stock leaves the warehouse),
                           book the shipment with the configured shipping provider
Out for Del. -> Delivered  create + submit the Sales Invoice; for a cash order the money is now
                           held by the agent until a COD Settlement records it (Payment Entry),
                           and for an order already paid online the advance is allocated to the
                           invoice so it is not left outstanding
Out for Del. -> Returned   submit a return Delivery Note (stock comes back), close the order
New/Confirmed -> Cancelled cancel the submitted Sales Order (a Draft one is kept, marked Cancelled)

Everything runs inside the save transaction: if any step fails, the status change is rolled back.
"""

import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice, make_sales_return
from frappe import _
from frappe.utils import flt

from store_core.providers.shipping.registry import get_provider as get_shipping_provider
from store_core.services.orders import system_context
from store_core.utils import status_machine as sm


def apply_status_change(assignment, previous_status: str):
	target = assignment.status
	handlers = {
		sm.CONFIRMED: _confirm,
		sm.OUT_FOR_DELIVERY: _dispatch,
		sm.DELIVERED: _deliver,
		sm.RETURNED: _return,
		sm.CANCELLED: _cancel,
	}
	handler = handlers.get(target)
	with system_context():
		if handler:
			handler(assignment)
		so_name = assignment.sales_order
		frappe.db.set_value("Sales Order", so_name, "lamsa_status", target, update_modified=False)
		if assignment.agent:
			update_agent_cash(assignment.agent)

	frappe.enqueue(
		"store_core.services.events.status_changed",
		queue="short",
		enqueue_after_commit=True,
		sales_order=assignment.sales_order,
		status=target,
	)


def _sales_order(assignment):
	return frappe.get_doc("Sales Order", assignment.sales_order)


def _confirm(assignment):
	so = _sales_order(assignment)
	if so.docstatus == 0:
		so.flags.ignore_permissions = True
		so.submit()
	elif so.docstatus == 2:
		frappe.throw(_("Sales Order {0} is cancelled").format(so.name))


def _dispatch(assignment):
	if not assignment.agent:
		frappe.throw(_("Select a Delivery Agent before sending the order out"))
	so = _sales_order(assignment)
	if so.docstatus != 1:
		frappe.throw(_("Confirm the order first"))
	if not assignment.delivery_note:
		dn = make_delivery_note(so.name)
		dn.flags.ignore_permissions = True
		dn.insert()
		dn.submit()
		assignment.delivery_note = dn.name
	shipment = get_shipping_provider().create_shipment(assignment)
	assignment.shipment_ref = shipment.reference
	_persist(assignment, "delivery_note", "shipment_ref")


def _deliver(assignment):
	if flt(assignment.collected_amount) <= 0 and assignment.payment_provider == "cod":
		assignment.collected_amount = flt(assignment.expected_amount)
	if not assignment.sales_invoice:
		si = make_sales_invoice(assignment.delivery_note)
		_allocate_prepayment(si, assignment)
		si.flags.ignore_permissions = True
		si.insert()
		si.submit()
		assignment.sales_invoice = si.name
	_persist(assignment, "sales_invoice", "collected_amount")


def _allocate_prepayment(si, assignment):
	"""An online payment was booked as an advance against the Sales Order: pull it into the invoice.

	Without this the money sits as an advance on the order while the invoice reads as fully
	outstanding, so the customer looks like a debtor for an order they already paid for.
	"""
	paid = frappe.db.get_value("Sales Order", assignment.sales_order, "lamsa_payment_status")
	if paid != "Paid":
		return
	si.allocate_advances_automatically = 1
	si.set_advances()


def _return(assignment):
	if assignment.delivery_note and not assignment.return_note:
		ret = make_sales_return(assignment.delivery_note)
		ret.flags.ignore_permissions = True
		ret.insert()
		ret.submit()
		assignment.return_note = ret.name
	assignment.collected_amount = 0
	so = _sales_order(assignment)
	if so.docstatus == 1 and so.status not in ("Closed", "Completed"):
		so.update_status("Closed")
	_persist(assignment, "return_note", "collected_amount")


def _cancel(assignment):
	so = _sales_order(assignment)
	if so.docstatus == 1:
		so.flags.ignore_permissions = True
		so.cancel()


def _persist(assignment, *fields):
	"""Write fields set during on_update without re-triggering save hooks."""
	for field in fields:
		assignment.db_set(field, assignment.get(field), update_modified=False)


def update_agent_cash(agent: str):
	"""Cash In Hand = collected on delivered orders not yet settled."""
	total = frappe.db.sql(
		"""select coalesce(sum(collected_amount), 0) from `tabDelivery Assignment`
		where agent=%s and status='Delivered' and settled=0""",
		agent,
	)[0][0]
	frappe.db.set_value("Delivery Agent", agent, "cash_in_hand", flt(total), update_modified=False)
