# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class DeliveryZone(Document):
	def validate(self):
		self.city = (self.city or "").strip()
		self.area = (self.area or "").strip()
		if flt(self.fee) < 0:
			frappe.throw(_("Delivery Fee cannot be negative"))
		if cint(self.est_days_min) < 0 or cint(self.est_days_max) < cint(self.est_days_min):
			frappe.throw(_("Estimated Days (max) must be greater than or equal to Estimated Days (min)"))
