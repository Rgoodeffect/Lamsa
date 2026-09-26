# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from store_core.utils.phone import InvalidPhone, normalize_libyan_phone


class LamsaSettings(Document):
	def validate(self):
		if self.whatsapp_number:
			try:
				self.whatsapp_number = normalize_libyan_phone(self.whatsapp_number)
			except InvalidPhone:
				frappe.throw(_("Store WhatsApp Number must be a valid Libyan mobile number"))

		for field in ("gift_wrap_item", "delivery_fee_item"):
			item = self.get(field)
			if item and frappe.db.get_value("Item", item, "is_stock_item"):
				frappe.throw(_("{0} must be a non-stock service item").format(self.meta.get_label(field)))

		if self.warehouse and self.company:
			if frappe.db.get_value("Warehouse", self.warehouse, "company") != self.company:
				frappe.throw(_("Store Warehouse must belong to {0}").format(self.company))

	def on_update(self):
		from store_core.services.catalog import invalidate_index

		invalidate_index()
