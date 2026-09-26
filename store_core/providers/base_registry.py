"""Hook-driven provider registry shared by payments, shipping and notifications.

A registry reads entries "code:dotted.path.Class" from a hooks key, so any installed app can add a
provider in its own hooks.py without touching store_core.
"""

import frappe
from frappe import _


class ProviderRegistry:
	def __init__(self, hook_name: str, kind: str):
		self.hook_name = hook_name
		self.kind = kind

	def entries(self) -> dict[str, str]:
		out: dict[str, str] = {}
		for entry in frappe.get_hooks(self.hook_name) or []:
			code, _sep, path = str(entry).partition(":")
			if code and path:
				out[code.strip()] = path.strip()  # later apps override earlier ones
		return out

	def codes(self) -> list[str]:
		return list(self.entries())

	def get(self, code: str):
		path = self.entries().get(code)
		if not path:
			frappe.throw(_("Unknown {0} provider: {1}").format(self.kind, code))
		cls = frappe.get_attr(path)
		instance = cls()
		instance.code = code
		return instance
