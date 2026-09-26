"""Manual shipping: the store's own delivery agents. Stub that satisfies the interface.

Tracking information lives on the Delivery Assignment itself, so this provider only echoes it.
Use it as a template for a real carrier (Aramex, DHL, a local Tripoli/Benghazi courier API).
"""

import frappe
from frappe.utils import now

from store_core.providers.shipping.base import Shipment, ShippingProvider, TrackingEvent


class ManualShipping(ShippingProvider):
	def create_shipment(self, assignment) -> Shipment:
		return Shipment(provider=self.code, reference=assignment.name, status="created")

	def get_label(self, shipment_ref: str):
		# The Delivery Note print format ("Lamsa Delivery Note") is the label for own agents.
		assignment = frappe.get_doc("Delivery Assignment", shipment_ref)
		if not assignment.delivery_note:
			return None
		return f"/printview?doctype=Delivery%20Note&name={assignment.delivery_note}&format=Lamsa%20Delivery%20Note"

	def track(self, shipment_ref: str) -> list[TrackingEvent]:
		status, changed = frappe.db.get_value(
			"Delivery Assignment", shipment_ref, ["status", "status_changed_on"]
		) or (None, None)
		if not status:
			return []
		return [TrackingEvent(status=status, timestamp=str(changed or now()))]
