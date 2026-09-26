"""Delivery Assignment status machine (pure Python, unit tested without a bench).

New -> Confirmed -> Out for Delivery -> Delivered | Returned
New | Confirmed -> Cancelled
"""

NEW = "New"
CONFIRMED = "Confirmed"
OUT_FOR_DELIVERY = "Out for Delivery"
DELIVERED = "Delivered"
RETURNED = "Returned"
CANCELLED = "Cancelled"

STATUSES = (NEW, CONFIRMED, OUT_FOR_DELIVERY, DELIVERED, RETURNED, CANCELLED)
FINAL_STATUSES = frozenset({DELIVERED, RETURNED, CANCELLED})

TRANSITIONS: dict[str, frozenset[str]] = {
	NEW: frozenset({CONFIRMED, CANCELLED}),
	CONFIRMED: frozenset({OUT_FOR_DELIVERY, CANCELLED}),
	OUT_FOR_DELIVERY: frozenset({DELIVERED, RETURNED}),
	DELIVERED: frozenset(),
	RETURNED: frozenset(),
	CANCELLED: frozenset(),
}

# Transitions a delivery agent may perform from the agent page; the rest are office-only.
AGENT_TRANSITIONS = frozenset({(OUT_FOR_DELIVERY, DELIVERED), (OUT_FOR_DELIVERY, RETURNED)})

# Customer-facing tracking steps (index used for the progress bar in the storefront).
TRACKING_STEPS = (NEW, CONFIRMED, OUT_FOR_DELIVERY, DELIVERED)


class InvalidTransition(ValueError):
	pass


def can_transition(current: str, target: str) -> bool:
	return target in TRANSITIONS.get(current, frozenset())


def assert_transition(current: str, target: str) -> None:
	if current == target:
		return
	if current not in TRANSITIONS or target not in TRANSITIONS:
		raise InvalidTransition(f"Unknown status: {current!r} -> {target!r}")
	if not can_transition(current, target):
		raise InvalidTransition(f"Cannot move from {current} to {target}")


def next_statuses(current: str) -> list[str]:
	return [s for s in STATUSES if s in TRANSITIONS.get(current, ())]


def is_agent_transition(current: str, target: str) -> bool:
	return (current, target) in AGENT_TRANSITIONS
