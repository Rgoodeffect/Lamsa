# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CODSettlement(Document):
	def validate(self):
		pass

	def on_submit(self):
		pass

	def on_cancel(self):
		pass
