import os

import frappe
from frappe import _


def get_settings():
	settings = frappe.get_cached_doc("Lamsa Settings")
	if not settings.company or not settings.selling_price_list or not settings.warehouse:
		frappe.throw(
			_("Lamsa Settings is not configured. Run store_core.setup.install.bootstrap first."),
			title=_("Store not configured"),
		)
	return settings


def get_secret(key: str, default: str | None = None) -> str | None:
	"""Secrets come from environment variables first, then site_config.json. Never from DocTypes.

	`LAMSA_REVALIDATE_SECRET` in the environment wins over `lamsa_revalidate_secret` in site_config.
	"""
	return os.environ.get(key.upper()) or frappe.conf.get(key.lower()) or default


def size_attribute() -> str:
	return frappe.get_cached_doc("Lamsa Settings").size_attribute or "Size"


def color_attribute() -> str:
	return frappe.get_cached_doc("Lamsa Settings").color_attribute or "Color"
