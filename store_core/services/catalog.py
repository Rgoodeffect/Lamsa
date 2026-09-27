"""Storefront catalog: a cached, denormalized product index built from ERPNext data.

Why an index: category pages need filters over variant attributes (size/color), prices from the
selling price list, stock from Bin and images from File. Building that once and caching it
(invalidated by doc_events on Item, Item Price, Item Group and Bin) keeps every storefront request
to a single Redis read. Suitable for catalogs up to a few thousand templates; beyond that, move the
index into a dedicated table.

All prices, stock and image paths come from ERPNext. Image paths are site-relative ("/files/..");
the storefront prefixes its ERP public URL.
"""

import re
from collections import defaultdict

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from store_core.services import pricing
from store_core.services.settings import color_attribute, get_settings, size_attribute
from store_core.utils.slug import slugify

INDEX_CACHE_KEY = "lamsa:catalog_index:v1"
INDEX_TTL_SECONDS = 600
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")
MAX_PAGE_SIZE = 48
SORTS = ("featured", "newest", "price_asc", "price_desc")


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def invalidate_index():
	frappe.cache.delete_value(INDEX_CACHE_KEY)


def get_index() -> dict:
	index = frappe.cache.get_value(INDEX_CACHE_KEY)
	if index is None:
		index = build_index()
		frappe.cache.set_value(INDEX_CACHE_KEY, index, expires_in_sec=INDEX_TTL_SECONDS)
	return index


def build_index() -> dict:
	settings = get_settings()
	size_attr, color_attr = size_attribute(), color_attribute()

	groups = _load_groups()
	templates = frappe.get_all(
		"Item",
		filters={"lamsa_publish": 1, "disabled": 0, "is_sales_item": 1, "variant_of": ["is", "not set"]},
		fields=[
			"name",
			"item_name",
			"item_group",
			"image",
			"description",
			"has_variants",
			"is_stock_item",
			"creation",
			"brand",
			"lamsa_slug",
			"lamsa_featured",
			"lamsa_gender",
			"lamsa_age_range",
			"lamsa_short_description_ar",
			"lamsa_description_ar",
			"lamsa_seo_title",
			"lamsa_seo_description",
		],
		order_by="creation desc",
	)
	template_codes = [t.name for t in templates]
	variants = (
		frappe.get_all(
			"Item",
			filters={"variant_of": ["in", template_codes], "disabled": 0, "is_sales_item": 1},
			fields=["name", "variant_of", "image", "is_stock_item"],
			order_by="name asc",
		)
		if template_codes
		else []
	)
	all_codes = template_codes + [v.name for v in variants]

	attributes = _load_variant_attributes([v.name for v in variants])
	value_meta = _load_attribute_values((size_attr, color_attr))
	prices = _load_prices(all_codes, settings.selling_price_list)
	discount_rules = pricing.catalog_discounts(settings, groups)
	stock = load_stock(all_codes, settings.warehouse)
	images = _load_images(all_codes)

	variants_by_template = defaultdict(list)
	for v in variants:
		variants_by_template[v.variant_of].append(v)

	products = []
	used_slugs = set()
	for t in templates:
		template_price = prices.get(t.name)
		product_variants = []
		if t.has_variants:
			for v in variants_by_template.get(t.name, []):
				list_price = prices.get(v.name, template_price)
				if list_price is None:
					continue
				# A variant inherits the template's item group and brand for rule matching.
				price = pricing.discounted(
					list_price, pricing.match(discount_rules, v.name, t.item_group, t.brand)
				)
				attrs = attributes.get(v.name, {})
				available = available_qty(stock, v.name, v.is_stock_item)
				product_variants.append(
					{
						"code": v.name,
						"attributes": attrs,
						"size": attrs.get(size_attr),
						"color": attrs.get(color_attr),
						"price": price,
						"list_price": list_price,
						"available": available,
						"in_stock": available > 0,
						"is_stock_item": cint(v.is_stock_item),
						"image": v.image or (images.get(v.name) or [None])[0],
						"images": images.get(v.name, []),
					}
				)
			if not product_variants:
				continue
			variant_prices = [pv["price"] for pv in product_variants]
			min_price, max_price = min(variant_prices), max(variant_prices)
			list_min_price = min(pv["list_price"] for pv in product_variants)
			list_max_price = max(pv["list_price"] for pv in product_variants)
			in_stock = any(pv["in_stock"] for pv in product_variants)
			available = sum(pv["available"] for pv in product_variants)
		else:
			if template_price is None:
				continue
			list_min_price = list_max_price = template_price
			min_price = max_price = pricing.discounted(
				template_price, pricing.match(discount_rules, t.name, t.item_group, t.brand)
			)
			available = available_qty(stock, t.name, t.is_stock_item)
			in_stock = available > 0

		slug = t.lamsa_slug or slugify(t.item_name) or slugify(t.name)
		if slug in used_slugs:
			slug = f"{slug}-{slugify(t.name)}"
		used_slugs.add(slug)

		gallery = _unique([t.image, *images.get(t.name, [])] + [pv["image"] for pv in product_variants])
		sizes = _ordered_values([pv["size"] for pv in product_variants], value_meta.get(size_attr, {}))
		colors = _ordered_values([pv["color"] for pv in product_variants], value_meta.get(color_attr, {}))
		group = groups.get(t.item_group) or {}

		products.append(
			{
				"code": t.name,
				"slug": slug,
				"name": t.item_name,
				"group": t.item_group,
				"group_slug": group.get("slug"),
				"image": gallery[0] if gallery else None,
				"images": gallery,
				"description": t.lamsa_description_ar or t.description or "",
				"short_description": t.lamsa_short_description_ar or "",
				"seo_title": t.lamsa_seo_title,
				"seo_description": t.lamsa_seo_description,
				"brand": t.brand,
				"gender": t.lamsa_gender,
				"age_range": t.lamsa_age_range,
				"featured": cint(t.lamsa_featured),
				"created": str(t.creation),
				"has_variants": cint(t.has_variants),
				"min_price": min_price,
				"max_price": max_price,
				# Price-list prices before any catalog discount, for the struck-through "was" price.
				"list_min_price": list_min_price,
				"list_max_price": list_max_price,
				"on_sale": list_max_price > max_price or list_min_price > min_price,
				"in_stock": in_stock,
				"available": available,
				"is_stock_item": cint(t.is_stock_item),
				"sizes": sizes,
				"colors": [
					{"name": c, "swatch": value_meta.get(color_attr, {}).get(c, {}).get("swatch")}
					for c in colors
				],
				"variants": product_variants,
				"search_text": normalize_arabic(
					" ".join(filter(None, [t.item_name, t.name, t.item_group, group.get("title"), t.brand]))
				),
			}
		)

	return {
		"currency": settings.currency,
		"size_attribute": size_attr,
		"color_attribute": color_attr,
		"groups": groups,
		"products": products,
	}


def available_qty(stock: dict, code: str, is_stock_item) -> float:
	if not cint(is_stock_item):
		return 9999
	return max(flt(stock.get(code, 0)), 0)


def _unique(values):
	seen, out = set(), []
	for v in values:
		if v and v not in seen:
			seen.add(v)
			out.append(v)
	return out


def _ordered_values(values, meta: dict) -> list[str]:
	present = {v for v in values if v}
	return sorted(present, key=lambda v: (meta.get(v, {}).get("idx", 9999), v))


def _load_groups() -> dict:
	rows = frappe.get_all(
		"Item Group",
		fields=[
			"name",
			"parent_item_group",
			"lft",
			"rgt",
			"is_group",
			"image",
			"lamsa_show_in_store",
			"lamsa_slug",
			"lamsa_title_ar",
			"lamsa_sort",
			"lamsa_size_guide",
			"lamsa_has_age_filter",
			"lamsa_description_ar",
		],
		order_by="lft asc",
	)
	groups = {}
	for g in rows:
		groups[g.name] = {
			"name": g.name,
			"parent": g.parent_item_group,
			"lft": g.lft,
			"rgt": g.rgt,
			"visible": cint(g.lamsa_show_in_store),
			"slug": g.lamsa_slug or slugify(g.name),
			"title": g.lamsa_title_ar or g.name,
			"description": g.lamsa_description_ar,
			"image": g.image,
			"sort": cint(g.lamsa_sort),
			"size_guide": g.lamsa_size_guide,
			"has_age_filter": cint(g.lamsa_has_age_filter),
		}
	return groups


def _load_variant_attributes(codes: list[str]) -> dict:
	if not codes:
		return {}
	rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", codes], "parenttype": "Item"},
		fields=["parent", "attribute", "attribute_value"],
		order_by="idx asc",
	)
	out = defaultdict(dict)
	for r in rows:
		out[r.parent][r.attribute] = r.attribute_value
	return dict(out)


def _load_attribute_values(attributes) -> dict:
	rows = frappe.get_all(
		"Item Attribute Value",
		filters={"parent": ["in", list(attributes)], "parenttype": "Item Attribute"},
		fields=["parent", "attribute_value", "lamsa_swatch", "idx"],
		order_by="idx asc",
	)
	out = defaultdict(dict)
	for r in rows:
		# Colour swatch from Item Attribute Value.lamsa_swatch (custom Color field)
		swatch = (
			r.lamsa_swatch if r.lamsa_swatch and re.fullmatch(r"#[0-9a-fA-F]{3,8}", r.lamsa_swatch) else None
		)
		out[r.parent][r.attribute_value] = {"idx": r.idx, "swatch": swatch}
	return dict(out)


def _load_prices(codes: list[str], price_list: str) -> dict:
	if not codes:
		return {}
	today = getdate(nowdate())
	rows = frappe.get_all(
		"Item Price",
		filters={"price_list": price_list, "item_code": ["in", codes]},
		fields=["item_code", "price_list_rate", "customer", "valid_from", "valid_upto", "batch_no"],
		order_by="valid_from asc, creation asc",
	)
	prices = {}
	for r in rows:
		if r.customer or r.batch_no:
			continue
		if r.valid_from and getdate(r.valid_from) > today:
			continue
		if r.valid_upto and getdate(r.valid_upto) < today:
			continue
		prices[r.item_code] = flt(r.price_list_rate)  # later valid_from wins
	return prices


def load_stock(codes: list[str], warehouse: str) -> dict:
	"""Sellable qty = actual - reserved (submitted orders) - qty held by unconfirmed store orders.

	Storefront orders stay Draft until staff confirm them, and drafts do not reserve stock in
	ERPNext, so they are subtracted here to avoid overselling.
	"""
	if not codes:
		return {}
	rows = frappe.get_all(
		"Bin",
		filters={"warehouse": warehouse, "item_code": ["in", codes]},
		fields=["item_code", "actual_qty", "reserved_qty"],
	)
	stock = {r.item_code: flt(r.actual_qty) - flt(r.reserved_qty) for r in rows}
	held = frappe.db.sql(
		"""
		select soi.item_code, sum(soi.stock_qty)
		from `tabSales Order Item` soi
		join `tabSales Order` so on so.name = soi.parent
		where so.docstatus = 0 and so.lamsa_status = 'New'
			and soi.warehouse = %s and soi.item_code in %s
		group by soi.item_code
		""",
		(warehouse, tuple(codes)),
	)
	for code, qty in held:
		stock[code] = stock.get(code, 0) - flt(qty)
	return stock


def _load_images(codes: list[str]) -> dict:
	if not codes:
		return {}
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Item", "attached_to_name": ["in", codes], "is_private": 0},
		fields=["attached_to_name", "file_url"],
		order_by="creation asc",
	)
	out = defaultdict(list)
	for r in rows:
		if r.file_url and r.file_url.lower().endswith(IMAGE_EXTENSIONS):
			out[r.attached_to_name].append(r.file_url)
	return dict(out)


# ---------------------------------------------------------------------------
# Arabic-aware search normalization
# ---------------------------------------------------------------------------

_AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"})


def normalize_arabic(text: str | None) -> str:
	if not text:
		return ""
	text = _AR_DIACRITICS.sub("", str(text).lower()).translate(_AR_FOLD)
	return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Queries used by the API
# ---------------------------------------------------------------------------


def group_descendants(index: dict, group_name: str) -> set[str]:
	groups = index["groups"]
	root = groups.get(group_name)
	if not root:
		return set()
	return {g["name"] for g in groups.values() if g["lft"] >= root["lft"] and g["rgt"] <= root["rgt"]}


def find_group_by_slug(index: dict, slug: str) -> dict | None:
	for g in index["groups"].values():
		if g["visible"] and g["slug"] == slug:
			return g
	return None


def category_tree(index: dict) -> list[dict]:
	groups = index["groups"]
	products = index["products"]
	counts = defaultdict(int)
	for p in products:
		group = groups.get(p["group"])
		if not group:
			continue
		for g in groups.values():
			if g["lft"] <= group["lft"] and g["rgt"] >= group["rgt"]:
				counts[g["name"]] += 1

	def node(g):
		children = [c for c in groups.values() if c["parent"] == g["name"] and c["visible"]]
		children.sort(key=lambda c: (c["sort"], c["title"]))
		return {
			"slug": g["slug"],
			"title": g["title"],
			"description": g["description"],
			"image": g["image"],
			"product_count": counts.get(g["name"], 0),
			"has_age_filter": g["has_age_filter"],
			"children": [node(c) for c in children],
		}

	visible = [g for g in groups.values() if g["visible"]]
	roots = [g for g in visible if not groups.get(g["parent"], {}).get("visible")]
	roots.sort(key=lambda g: (g["sort"], g["title"]))
	return [node(g) for g in roots]


def breadcrumbs(index: dict, group_name: str) -> list[dict]:
	groups = index["groups"]
	trail = []
	g = groups.get(group_name)
	while g:
		if g["visible"]:
			trail.append({"slug": g["slug"], "title": g["title"]})
		g = groups.get(g["parent"])
	return list(reversed(trail))


def filter_products(
	index: dict,
	category: str | None = None,
	sizes: list[str] | None = None,
	colors: list[str] | None = None,
	age_ranges: list[str] | None = None,
	min_price: float | None = None,
	max_price: float | None = None,
	in_stock: bool = False,
	featured: bool = False,
	on_sale: bool = False,
	query: str | None = None,
) -> list[dict]:
	products = index["products"]

	if category:
		group = find_group_by_slug(index, category)
		if not group:
			return []
		allowed = group_descendants(index, group["name"])
		products = [p for p in products if p["group"] in allowed]

	if featured:
		products = [p for p in products if p["featured"]]

	if on_sale:
		products = [p for p in products if p["on_sale"]]

	if age_ranges:
		wanted = set(age_ranges)
		products = [p for p in products if p["age_range"] in wanted]

	if sizes or colors or in_stock:
		wanted_sizes, wanted_colors = set(sizes or []), set(colors or [])

		def variant_matches(v):
			return (
				(not wanted_sizes or v["size"] in wanted_sizes)
				and (not wanted_colors or v["color"] in wanted_colors)
				and (not in_stock or v["in_stock"])
			)

		def product_matches(p):
			if p["has_variants"]:
				return any(variant_matches(v) for v in p["variants"])
			# Simple items have no size/colour; they only survive the stock filter.
			return not wanted_sizes and not wanted_colors and (not in_stock or p["in_stock"])

		products = [p for p in products if product_matches(p)]

	if min_price is not None:
		products = [p for p in products if p["max_price"] >= flt(min_price)]
	if max_price is not None:
		products = [p for p in products if p["min_price"] <= flt(max_price)]

	if query:
		tokens = normalize_arabic(query).split()
		if not tokens:
			return []
		scored = []
		for p in products:
			if all(t in p["search_text"] for t in tokens):
				name = normalize_arabic(p["name"])
				score = sum(3 if name.startswith(t) else 2 if t in name else 1 for t in tokens)
				scored.append((score, p))
		scored.sort(key=lambda sp: (-sp[0], not sp[1]["in_stock"]))
		products = [p for _, p in scored]

	return products


def sort_products(products: list[dict], sort: str) -> list[dict]:
	if sort == "price_asc":
		return sorted(products, key=lambda p: p["min_price"])
	if sort == "price_desc":
		return sorted(products, key=lambda p: -p["max_price"])
	if sort == "newest":
		return sorted(products, key=lambda p: p["created"], reverse=True)
	# featured: featured first, in-stock first, then newest (sorted() is stable)
	newest_first = sorted(products, key=lambda p: p["created"], reverse=True)
	return sorted(newest_first, key=lambda p: (not p["featured"], not p["in_stock"]))


def facets(index: dict, products: list[dict]) -> dict:
	size_order, color_seen = {}, {}
	for p in products:
		for i, s in enumerate(p["sizes"]):
			size_order.setdefault(s, (len(size_order), i))
		for c in p["colors"]:
			color_seen.setdefault(c["name"], c)
	ages_present = {p["age_range"] for p in products if p["age_range"]}
	ages = (
		frappe.get_all(
			"Age Range",
			filters={"name": ["in", list(ages_present)]},
			fields=["name", "label", "min_months", "max_months", "sort_order"],
			order_by="sort_order asc, min_months asc",
		)
		if ages_present
		else []
	)
	prices = [p["min_price"] for p in products] + [p["max_price"] for p in products]
	return {
		"sizes": list(size_order),
		"colors": list(color_seen.values()),
		"age_ranges": [{"name": a.name, "label": a.label} for a in ages],
		"price": {"min": min(prices) if prices else 0, "max": max(prices) if prices else 0},
	}


def product_card(p: dict) -> dict:
	return {
		"code": p["code"],
		"slug": p["slug"],
		"name": p["name"],
		"image": p["image"],
		"hover_image": p["images"][1] if len(p["images"]) > 1 else None,
		"min_price": p["min_price"],
		"max_price": p["max_price"],
		"list_min_price": p["list_min_price"],
		"list_max_price": p["list_max_price"],
		"on_sale": p["on_sale"],
		"in_stock": p["in_stock"],
		"colors": p["colors"],
		"group_slug": p["group_slug"],
		"featured": p["featured"],
	}


def paginate(items: list, page: int, page_size: int) -> tuple[list, dict]:
	page_size = max(1, min(cint(page_size) or 24, MAX_PAGE_SIZE))
	page = max(1, cint(page) or 1)
	total = len(items)
	start = (page - 1) * page_size
	return items[start : start + page_size], {
		"page": page,
		"page_size": page_size,
		"total": total,
		"pages": (total + page_size - 1) // page_size,
	}


def find_product(index: dict, slug: str) -> dict | None:
	for p in index["products"]:
		if p["slug"] == slug:
			return p
	return None


def find_sellable(index: dict, item_code: str) -> tuple[dict, dict | None] | tuple[None, None]:
	"""Return (product, variant) for a sellable item code, or (None, None)."""
	for p in index["products"]:
		if p["has_variants"]:
			for v in p["variants"]:
				if v["code"] == item_code:
					return p, v
		elif p["code"] == item_code:
			return p, None
	return None, None


def size_guide_for(index: dict, group_name: str) -> dict | None:
	groups = index["groups"]
	g = groups.get(group_name)
	while g and not g["size_guide"]:
		g = groups.get(g["parent"])
	if not g:
		return None
	guide = frappe.get_cached_doc("Size Guide", g["size_guide"])
	columns = [
		f
		for f in ("size", "age_label", "chest", "waist", "hips", "length", "height")
		if any(row.get(f) for row in guide.rows)
	]
	return {
		"title": guide.title,
		"notes": guide.notes,
		"columns": columns,
		"rows": [{c: row.get(c) for c in columns} for row in guide.rows],
	}


def low_stock_label(available: float) -> dict:
	settings = frappe.get_cached_doc("Lamsa Settings")
	threshold = cint(settings.low_stock_threshold) or 3
	max_qty = cint(settings.max_qty_per_line) or 10
	if available <= 0:
		return {"status": "out", "max_qty": 0}
	if available <= threshold:
		return {"status": "low", "left": int(available), "max_qty": min(int(available), max_qty)}
	return {"status": "in", "max_qty": min(int(available), max_qty)}
