"""Find-or-create the ERPNext Customer, Contact and Address for a storefront order.

Customers are matched by the normalized Libyan mobile number stored in Customer.lamsa_phone.
"""

import frappe
from frappe import _

from store_core.services.settings import get_settings
from store_core.utils.phone import InvalidPhone, normalize_libyan_phone


def customer_validate(doc, method=None):
	"""doc_event: keep Customer.lamsa_phone normalized when edited from the desk."""
	if doc.get("lamsa_phone"):
		try:
			doc.lamsa_phone = normalize_libyan_phone(doc.lamsa_phone)
		except InvalidPhone:
			frappe.throw(_("Store Phone must be a valid Libyan mobile number"))


def get_or_create_customer(full_name: str, phone: str) -> str:
	"""Return the Customer name for this phone, creating Customer + Contact if needed."""
	existing = frappe.db.get_value("Customer", {"lamsa_phone": phone, "disabled": 0}, "name")
	if existing:
		return existing

	settings = get_settings()
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": full_name,
			"customer_type": "Individual",
			"customer_group": settings.customer_group,
			"territory": settings.territory,
			"lamsa_phone": phone,
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()

	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": full_name,
			"phone_nos": [{"phone": phone, "is_primary_mobile_no": 1}],
			"links": [{"link_doctype": "Customer", "link_name": customer.name}],
		}
	)
	contact.flags.ignore_permissions = True
	contact.insert()

	frappe.db.set_value("Customer", customer.name, "customer_primary_contact", contact.name)
	return customer.name


def get_primary_contact(customer: str) -> str | None:
	return frappe.db.get_value("Customer", customer, "customer_primary_contact")


def get_or_create_address(customer: str, full_name: str, phone: str, city: str, area: str, notes: str) -> str:
	"""Reuse an identical shipping address for this customer, otherwise create one."""
	line1 = area.strip()
	line2 = (notes or "").strip()[:240]
	rows = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
		pluck="parent",
	)
	if rows:
		match = frappe.db.get_value(
			"Address",
			{
				"name": ["in", rows],
				"city": city,
				"address_line1": line1,
				"address_line2": line2 or ["is", "not set"],
			},
			"name",
		)
		if match:
			return match

	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": full_name,
			"address_type": "Shipping",
			"address_line1": line1,
			"address_line2": line2 or None,
			"city": city,
			"country": _libya(),
			"phone": phone,
			"is_shipping_address": 1,
			"links": [{"link_doctype": "Customer", "link_name": customer}],
		}
	)
	address.flags.ignore_permissions = True
	address.insert()
	return address.name


def _libya() -> str:
	return "Libya" if frappe.db.exists("Country", "Libya") else frappe.db.get_default("country")
