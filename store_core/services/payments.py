"""Recording an online payment against a store order.

Cash orders are settled through COD Settlement (one Payment Entry per invoice, at the end of the
day). An online payment is different: the money arrives *before* delivery, so it is booked as an
advance Payment Entry against the Sales Order. When the Sales Invoice is created at delivery,
ERPNext allocates that advance to it.

`record_payment` is the single entry point for every online provider and is idempotent, because
gateways retry their callbacks.
"""

import frappe
from frappe import _
from frappe.utils import flt

from store_core.services.settings import get_settings

PAID = "Paid"
UNPAID = "Unpaid"
FAILED = "Failed"
#: Tolerance when comparing the gateway amount with the order total (rounding in minor units).
AMOUNT_TOLERANCE = 0.01


class PaymentError(frappe.ValidationError):
	pass


def find_order(order_no: str):
	"""The Sales Order behind a store order number, or None."""
	name = frappe.db.get_value("Sales Order", {"lamsa_order_no": order_no}, "name")
	return frappe.get_doc("Sales Order", name) if name else None


def amounts_match(paid: float, expected: float) -> bool:
	return abs(flt(paid) - flt(expected)) <= AMOUNT_TOLERANCE


def order_total(so) -> float:
	return flt(so.rounded_total or so.grand_total)


def record_payment(so, provider: str, reference: str, amount: float, mode_of_payment: str | None = None) -> dict:
	"""Submit the order, book the money as an advance Payment Entry, and mark the order paid.

	Idempotent: a second callback with the same reference returns the first result instead of
	booking the money twice.
	"""
	_lock_order(so)
	if so.lamsa_payment_status == PAID and (so.lamsa_payment_reference or "") == reference:
		return {"status": PAID, "reference": reference, "payment_entry": _existing_entry(so), "duplicate": True}
	if so.lamsa_payment_status == PAID:
		# Paid already, but with a different reference: do not book twice, make it visible instead.
		frappe.log_error(
			title=f"Lamsa: second payment for order {so.lamsa_order_no}",
			message=f"already paid with {so.lamsa_payment_reference}, now {provider} sent {reference}",
		)
		raise PaymentError(_("Order {0} is already paid").format(so.lamsa_order_no))

	if not amounts_match(amount, order_total(so)):
		raise PaymentError(
			_("Paid amount {0} does not match the order total {1}").format(amount, order_total(so))
		)

	if so.docstatus == 2:
		raise PaymentError(_("Order {0} is cancelled").format(so.lamsa_order_no))
	if so.docstatus == 0:
		so.flags.ignore_permissions = True
		so.submit()  # reserves the stock; the order is paid for, so it is no longer provisional

	entry = _create_payment_entry(so, provider, reference, amount, mode_of_payment)
	so.db_set("lamsa_payment_status", PAID, update_modified=False)
	so.db_set("lamsa_payment_reference", reference, update_modified=False)
	_update_assignment(so, provider)
	return {"status": PAID, "reference": reference, "payment_entry": entry, "duplicate": False}


def record_failure(so, provider: str, reason: str | None = None):
	"""A failed or cancelled attempt: leave the draft order alone so the customer can retry."""
	if so.lamsa_payment_status == PAID:
		return
	so.db_set("lamsa_payment_status", FAILED, update_modified=False)
	so.add_comment("Info", _("Payment failed ({0}): {1}").format(provider, reason or ""))


def _lock_order(so):
	"""Serialize concurrent callbacks for the same order.

	Gateways retry, and a widget can fire its callback twice, so two requests can arrive together.
	Locking the row here means the second one waits and then sees the order as already paid instead
	of booking a second Payment Entry.
	"""
	row = frappe.db.sql(
		"select lamsa_payment_status, lamsa_payment_reference from `tabSales Order` where name = %s for update",
		(so.name,),
		as_dict=True,
	)
	if row:
		so.lamsa_payment_status = row[0].lamsa_payment_status
		so.lamsa_payment_reference = row[0].lamsa_payment_reference


def _existing_entry(so) -> str | None:
	return frappe.db.get_value(
		"Payment Entry Reference",
		{"reference_doctype": "Sales Order", "reference_name": so.name, "docstatus": 1},
		"parent",
	)


def _create_payment_entry(so, provider: str, reference: str, amount: float, mode_of_payment: str | None) -> str:
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	settings = get_settings()
	account = settings.online_payment_account
	if not account:
		raise PaymentError(
			_("Set an Online Payment Account in Lamsa Settings before enabling online payments")
		)

	# bank_account is how ERPNext is told where the money landed; setting paid_to afterwards would
	# leave its currency and conversion fields as the company default.
	entry = get_payment_entry(
		"Sales Order",
		so.name,
		party_amount=flt(amount),
		bank_account=account,
		bank_amount=flt(amount),
	)
	entry.paid_amount = flt(amount)
	entry.received_amount = flt(amount)
	entry.reference_no = reference
	entry.reference_date = frappe.utils.nowdate()
	if mode_of_payment and frappe.db.exists("Mode of Payment", mode_of_payment):
		entry.mode_of_payment = mode_of_payment
	entry.remarks = _("Online payment for store order {0} via {1}").format(so.lamsa_order_no, provider)
	entry.flags.ignore_permissions = True
	entry.insert()
	entry.submit()
	return entry.name


def _update_assignment(so, provider: str):
	"""A prepaid order has nothing for the agent to collect."""
	name = frappe.db.get_value("Delivery Assignment", {"sales_order": so.name}, "name")
	if not name:
		return
	frappe.db.set_value(
		"Delivery Assignment",
		name,
		{"expected_amount": 0, "payment_provider": provider},
		update_modified=False,
	)
	frappe.get_doc("Delivery Assignment", name).add_comment(
		"Info", _("Paid online via {0} — nothing to collect on delivery").format(provider)
	)
