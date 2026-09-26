# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class AgeRange(Document):
	def validate(self):
		if self.max_months and cint(self.max_months) < cint(self.min_months):
			frappe.throw(_("Max Age must be greater than or equal to Min Age"))
