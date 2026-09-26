# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from store_core.utils.phone import InvalidPhone, normalize_libyan_phone


class DeliveryAgent(Document):
	def validate(self):
		try:
			self.phone = normalize_libyan_phone(self.phone)
		except InvalidPhone:
			frappe.throw(_("Phone must be a valid Libyan mobile number"))
		if self.user and "Lamsa Delivery Agent" not in frappe.get_roles(self.user):
			frappe.msgprint(
				_(
					"User {0} does not have the Lamsa Delivery Agent role yet, so the agent page will not open."
				).format(self.user),
				indicator="orange",
				alert=True,
			)
