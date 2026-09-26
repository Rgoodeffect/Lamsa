"""Ordered placeholder names of each message template.

WhatsApp template messages take *positional* parameters ({{1}}, {{2}}, ...), while TEMPLATES here
are written with named Python placeholders. The order a name first appears in the text is the
position it must occupy in the approved Meta template, so the order is derived from the text itself
rather than kept in a second list that could drift out of step.
"""

from string import Formatter

from store_core.providers.notifications.templates import TEMPLATES


def placeholders(template: str) -> list[str]:
	"""["customer_name", "order_no", ...] in the order they appear in the template text."""
	text = TEMPLATES.get(template)
	if not text:
		return []
	out: list[str] = []
	for _literal, field, _spec, _conv in Formatter().parse(text):
		if field and field not in out:
			out.append(field)
	return out


def ordered_values(template: str, context: dict) -> list[str]:
	"""Context values as positional WhatsApp body parameters.

	WhatsApp rejects newlines, tabs and runs of 4+ spaces inside a parameter, so they are collapsed.
	"""
	return [_clean(context.get(name, "")) for name in placeholders(template)]


def _clean(value) -> str:
	return " ".join(str(value if value is not None else "").split())
