# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from store_core.utils import status_machine as sm


class DeliveryAssignment(Document):
	def validate(self):
		previous = self.get_doc_before_save()
		self._status_changed_from = None
		if previous and previous.status != self.status:
			try:
				sm.assert_transition(previous.status, self.status)
			except sm.InvalidTransition:
				frappe.throw(
					_("Cannot change status from {0} to {1}").format(_(previous.status), _(self.status)),
					title=_("Invalid status change"),
				)
			if self.status == sm.OUT_FOR_DELIVERY and not self.agent:
				frappe.throw(_("Select a Delivery Agent before sending the order out"))
			self.status_changed_on = now_datetime()
			self._status_changed_from = previous.status

		if previous and previous.status in sm.FINAL_STATUSES and self.has_value_changed("agent"):
			frappe.throw(_("Cannot change the agent of a closed assignment"))
		if previous and previous.settled and self.has_value_changed("collected_amount"):
			frappe.throw(_("Collected amount cannot change after the cash was settled"))
		if flt(self.collected_amount) < 0:
			frappe.throw(_("Collected Amount cannot be negative"))

	def on_update(self):
		if getattr(self, "_status_changed_from", None):
			from store_core.services.delivery_flow import apply_status_change

			apply_status_change(self, self._status_changed_from)
		elif self.agent and self.has_value_changed("collected_amount"):
			from store_core.services.delivery_flow import update_agent_cash

			update_agent_cash(self.agent)

	def on_trash(self):
		if self.status != sm.NEW:
			frappe.throw(_("Only new assignments can be deleted"))
