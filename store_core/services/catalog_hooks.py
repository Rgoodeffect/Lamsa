"""doc_events that keep store fields on Item / Item Group consistent."""

import frappe
from frappe import _

from store_core.utils.slug import slugify


def item_before_validate(doc, method=None):
	if doc.get("variant_of"):
		return
	if doc.get("lamsa_publish") and not doc.get("lamsa_slug"):
		doc.lamsa_slug = _unique_slug("Item", slugify(doc.item_name) or slugify(doc.item_code), doc.name)
	elif doc.get("lamsa_slug"):
		slug = slugify(doc.lamsa_slug)
		if _slug_taken("Item", slug, doc.name):
			frappe.throw(_("URL Slug {0} is already used by another item").format(slug))
		doc.lamsa_slug = slug


def item_group_before_validate(doc, method=None):
	if doc.get("lamsa_show_in_store") and not doc.get("lamsa_slug"):
		doc.lamsa_slug = _unique_slug("Item Group", slugify(doc.item_group_name), doc.name)
	elif doc.get("lamsa_slug"):
		slug = slugify(doc.lamsa_slug)
		if _slug_taken("Item Group", slug, doc.name):
			frappe.throw(_("URL Slug {0} is already used by another item group").format(slug))
		doc.lamsa_slug = slug


def _slug_taken(doctype: str, slug: str, name: str | None) -> bool:
	return bool(frappe.db.exists(doctype, {"lamsa_slug": slug, "name": ["!=", name or ""]}))


def _unique_slug(doctype: str, base: str, name: str | None) -> str:
	base = base or frappe.generate_hash(length=8)
	slug, n = base, 2
	while _slug_taken(doctype, slug, name):
		slug = f"{base}-{n}"
		n += 1
	return slug
