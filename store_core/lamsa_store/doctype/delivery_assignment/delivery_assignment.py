# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from store_core.utils import status_machine as sm


class DeliveryAssignment(Document):
	def validate(self):
		previous = self.get_doc_before_save()
		if previous and previous.status != self.status:
			try:
				sm.assert_transition(previous.status, self.status)
			except sm.InvalidTransition:
				frappe.throw(
					_("Cannot change status from {0} to {1}").format(_(previous.status), _(self.status)),
					title=_("Invalid status change"),
				)
			self.status_changed_on = now_datetime()
		if previous and previous.status in sm.FINAL_STATUSES and self.has_value_changed("agent"):
			frappe.throw(_("Cannot change the agent of a closed assignment"))
