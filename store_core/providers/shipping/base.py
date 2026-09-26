"""Shipping provider interface (local couriers now, international carriers later).

Phase 1 delivers with the store's own agents (Delivery Assignment). A carrier integration
implements this interface and is selected in Lamsa Settings > Shipping Provider.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field


@dataclass
class Shipment:
	provider: str
	reference: str | None = None  # carrier tracking / waybill number
	status: str = "created"
	label_url: str | None = None
	extra: dict = field(default_factory=dict)

	def as_dict(self) -> dict:
		return asdict(self)


@dataclass
class TrackingEvent:
	status: str  # normalized to Delivery Assignment statuses where possible
	timestamp: str
	description: str | None = None
	location: str | None = None


class ShippingProvider(ABC):
	code: str = ""

	@abstractmethod
	def create_shipment(self, assignment) -> Shipment:
		"""Book a pickup/waybill for a Delivery Assignment."""

	@abstractmethod
	def get_label(self, shipment_ref: str) -> bytes | str | None:
		"""Return a PDF (bytes) or a URL for the shipping label."""

	@abstractmethod
	def track(self, shipment_ref: str) -> list[TrackingEvent]:
		"""Return tracking events, newest last."""

	def cancel(self, shipment_ref: str) -> bool:
		raise NotImplementedError
