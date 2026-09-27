"""Catalog endpoints: /api/method/store_core.api.v1.catalog.<name>"""

import frappe
from frappe.utils import cint, flt

from store_core.services import catalog
from store_core.services.orders import CheckoutError
from store_core.utils.api import parse_list, storefront_endpoint


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_categories():
	index = catalog.get_index()
	return {"currency": index["currency"], "categories": catalog.category_tree(index)}


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_products(
	category: str | None = None,
	sizes: str | list | None = None,
	colors: str | list | None = None,
	age_ranges: str | list | None = None,
	min_price: str | float | None = None,
	max_price: str | float | None = None,
	in_stock: str | int | bool | None = None,
	featured: str | int | bool | None = None,
	on_sale: str | int | bool | None = None,
	sort: str | None = None,
	page: str | int | None = 1,
	page_size: str | int | None = 24,
):
	index = catalog.get_index()
	group = None
	if category:
		group = catalog.find_group_by_slug(index, category)
		if not group:
			raise CheckoutError("category_not_found")

	scoped = catalog.filter_products(index, category=category, on_sale=bool(cint(on_sale)))
	products = catalog.filter_products(
		index,
		category=category,
		sizes=parse_list(sizes),
		colors=parse_list(colors),
		age_ranges=parse_list(age_ranges),
		min_price=flt(min_price) if min_price not in (None, "") else None,
		max_price=flt(max_price) if max_price not in (None, "") else None,
		in_stock=bool(cint(in_stock)),
		featured=bool(cint(featured)),
		on_sale=bool(cint(on_sale)),
	)
	products = catalog.sort_products(products, sort if sort in catalog.SORTS else "featured")
	page_items, pagination = catalog.paginate(products, page, page_size)

	return {
		"currency": index["currency"],
		"category": _category_info(index, group) if group else None,
		"products": [catalog.product_card(p) for p in page_items],
		"pagination": pagination,
		"facets": catalog.facets(index, scoped),
	}


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_product(slug: str):
	index = catalog.get_index()
	p = catalog.find_product(index, slug)
	if not p:
		raise CheckoutError("product_not_found")

	related = [
		catalog.product_card(r)
		for r in catalog.sort_products(
			[r for r in index["products"] if r["group"] == p["group"] and r["code"] != p["code"]], "featured"
		)[:8]
	]
	variants = [
		{
			"code": v["code"],
			"size": v["size"],
			"color": v["color"],
			"attributes": v["attributes"],
			"price": v["price"],
			"list_price": v["list_price"],
			"image": v["image"],
			"stock": catalog.low_stock_label(v["available"]),
		}
		for v in p["variants"]
	]
	return {
		"currency": index["currency"],
		"product": {
			"code": p["code"],
			"slug": p["slug"],
			"name": p["name"],
			"description": p["description"],
			"short_description": p["short_description"],
			"seo_title": p["seo_title"],
			"seo_description": p["seo_description"],
			"brand": p["brand"],
			"images": p["images"],
			"min_price": p["min_price"],
			"max_price": p["max_price"],
			"list_min_price": p["list_min_price"],
			"list_max_price": p["list_max_price"],
			"on_sale": p["on_sale"],
			"in_stock": p["in_stock"],
			"has_variants": p["has_variants"],
			"stock": None if p["has_variants"] else catalog.low_stock_label(p["available"]),
			"sizes": p["sizes"],
			"colors": p["colors"],
			"variants": variants,
			"age_range": p["age_range"],
			"group_slug": p["group_slug"],
			"breadcrumbs": catalog.breadcrumbs(index, p["group"]),
			"size_guide": catalog.size_guide_for(index, p["group"]),
		},
		"related": related,
	}


@frappe.whitelist(methods=["GET"])
@storefront_endpoint(rate_limit=(60, 60))
def search(q: str, page: str | int | None = 1, page_size: str | int | None = 24):
	q = (q or "").strip()[:80]
	index = catalog.get_index()
	products = catalog.filter_products(index, query=q) if q else []
	page_items, pagination = catalog.paginate(products, page, page_size)
	return {
		"currency": index["currency"],
		"query": q,
		"products": [catalog.product_card(p) for p in page_items],
		"pagination": pagination,
	}


@frappe.whitelist(methods=["POST"])
@storefront_endpoint(rate_limit=(20, 300))
def search_by_image(image: str, limit: str | int | None = 12):
	"""Products that look like an uploaded photo. `image` is base64 (a data: URL is accepted).

	Rate limited harder than text search: encoding an image costs real CPU on the same box as ERPNext.
	The photo is used for this call only and never stored.
	"""
	from store_core.services import image_search

	settings = frappe.get_cached_doc("Lamsa Settings")
	if not cint(settings.image_search_enabled):
		raise CheckoutError("image_search_unavailable")
	return image_search.search(_decode_image(image), limit=cint(limit) or 12)


def _decode_image(value: str) -> bytes:
	import base64
	import binascii

	raw = str(value or "")
	if raw.startswith("data:"):
		_header, _sep, raw = raw.partition(",")
	# 4/3 of the byte cap, plus slack for padding and newlines
	if len(raw) > 12 * 1024 * 1024:
		raise CheckoutError("image_too_large")
	try:
		return base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError):
		raise CheckoutError("image_unreadable")


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def get_sitemap():
	"""Slugs and last-modified hints for sitemap.xml."""
	index = catalog.get_index()
	return {
		"categories": [g["slug"] for g in index["groups"].values() if g["visible"]],
		"products": [{"slug": p["slug"], "updated": p["created"]} for p in index["products"]],
	}


def _category_info(index, group):
	return {
		"slug": group["slug"],
		"title": group["title"],
		"description": group["description"],
		"image": group["image"],
		"has_age_filter": group["has_age_filter"],
		"breadcrumbs": catalog.breadcrumbs(index, group["name"]),
		"children": [
			{"slug": g["slug"], "title": g["title"], "image": g["image"]}
			for g in sorted(index["groups"].values(), key=lambda g: (g["sort"], g["title"]))
			if g["parent"] == group["name"] and g["visible"]
		],
	}
