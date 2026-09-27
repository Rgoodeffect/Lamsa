"""Work out what seeding a product file would change — pure Python, no frappe, no database.

Keeping the planning separate from the writing is what makes `--dry-run` trustworthy: the plan is
computed here and printed, and `seed_products.apply_plan` then carries out exactly the operations it
lists. It also means the rules that matter — which SKU becomes which item, what a variable product
expands into, what is refused as bad data — are unit tested without a bench.

Nothing here talks to ERPNext, so the plan describes *intent*. Whether each item already exists, and
therefore whether an operation is a create or an update, is decided at apply time against the site.
"""

import json
from pathlib import Path

#: The store's categories. Created when missing, matched on the Item Group name.
CATEGORIES = {
	"gifts": {"name": "Gifts", "title_ar": "الهدايا", "sort": 10},
	"accessories": {"name": "Accessories", "title_ar": "الإكسسوارات", "sort": 20},
	"women": {"name": "Women", "title_ar": "ملابس نسائية", "sort": 30},
	"kids": {"name": "Kids", "title_ar": "ملابس أطفال", "sort": 40},
}
TYPES = ("simple", "variable", "bundle")
#: The Item Attribute a variable product's sizes become.
SIZE_ATTRIBUTE = "Size"


class SeedDataError(ValueError):
	"""The seed file is wrong in a way that would create bad data."""


def load(path: str | Path) -> list[dict]:
	raw = Path(path).read_text(encoding="utf-8")
	try:
		data = json.loads(raw)
	except json.JSONDecodeError as exc:
		raise SeedDataError(f"{path} is not valid JSON: {exc}") from exc
	if not isinstance(data, list):
		raise SeedDataError(f"{path} must contain a list of products")
	return data


def build_plan(products: list[dict]) -> dict:
	"""Validate the file and describe every category, item and price it implies."""
	validate(products)
	categories = [
		{"slug": slug, **CATEGORIES[slug]}
		# dict.fromkeys keeps the file's order and drops repeats
		for slug in dict.fromkeys(p["category"] for p in products)
	]
	items: list[dict] = []
	prices: list[dict] = []
	sizes: list[str] = []

	for product in products:
		items.append(_template(product))

		if product["type"] == "variable":
			for variant in product["variants"]:
				items.append(_variant(product, variant))
				prices.append({"item_code": variant["sku"], "rate": product["price_lyd"]})
				if variant["size"] not in sizes:
					sizes.append(variant["size"])
		else:
			# ERPNext v16 refuses an Item Price on a template, so only sellable codes get one.
			prices.append({"item_code": product["sku"], "rate": product["price_lyd"]})

	return {
		"categories": categories,
		"items": items,
		"prices": prices,
		"size_values": sizes,
		"bundles": [
			{"sku": p["sku"], "components": list(p["bundle_components"])}
			for p in products
			if p["type"] == "bundle" and p.get("bundle_components")
		],
		"warnings": warnings(products),
	}


def _template(product: dict) -> dict:
	"""The Item a customer browses to. A bundle is not a stock item: ERPNext stocks its parts."""
	is_bundle = product["type"] == "bundle"
	variable = product["type"] == "variable"
	return {
		"item_code": product["sku"],
		"role": "template" if variable else "sellable",
		"item_name": product["name_ar"],
		"name_en": product.get("name_en") or "",
		"item_group": CATEGORIES[product["category"]]["name"],
		"slug": product["slug"],
		"has_variants": 1 if variable else 0,
		"is_stock_item": 0 if is_bundle else 1,
		"stock": None if variable else product.get("stock"),
		"weight_g": product.get("weight_g"),
		"short_description_ar": product.get("short_description_ar") or "",
		"description_ar": product.get("description_ar") or "",
		"featured": 1 if product.get("featured") else 0,
		"tags": list(product.get("tags") or []),
		"supplier": product.get("supplier") or "",
		# Internal: stored behind permlevel 1 and never returned by a storefront endpoint.
		"cost_usd": product.get("cost_usd"),
		"supplier_url": product.get("supplier_url") or "",
		"note_internal": product.get("note_internal") or "",
		# The goods have not arrived and the storefront has no pre-order path, so nothing is published
		# yet: publishing an out-of-stock item would only show the customer a dead product.
		"publish": 0,
	}


def _variant(product: dict, variant: dict) -> dict:
	return {
		"item_code": variant["sku"],
		"role": "variant",
		"variant_of": product["sku"],
		"item_name": f"{product['name_ar']} - {variant['size']}",
		"item_group": CATEGORIES[product["category"]]["name"],
		"attributes": {SIZE_ATTRIBUTE: variant["size"]},
		"stock": variant.get("stock"),
		"weight_g": product.get("weight_g"),
		"is_stock_item": 1,
	}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(products: list[dict]):
	"""Refuse a file that would create bad data, naming the product that is wrong."""
	if not products:
		raise SeedDataError("the seed file has no products")

	seen_skus: set[str] = set()
	seen_slugs: set[str] = set()
	for index, product in enumerate(products):
		where = f"product {index + 1}"
		for field in ("sku", "name_ar", "slug", "category", "type", "price_lyd"):
			if not product.get(field):
				raise SeedDataError(f"{where}: {field} is required")

		sku = product["sku"]
		if sku in seen_skus:
			raise SeedDataError(f"{where}: SKU {sku} appears twice")
		seen_skus.add(sku)
		if product["slug"] in seen_slugs:
			raise SeedDataError(f"{where}: slug {product['slug']} appears twice")
		seen_slugs.add(product["slug"])
		if product["category"] not in CATEGORIES:
			raise SeedDataError(f"{sku}: unknown category {product['category']}")
		if product["type"] not in TYPES:
			raise SeedDataError(f"{sku}: type must be one of {', '.join(TYPES)}")
		if float(product["price_lyd"]) <= 0:
			raise SeedDataError(f"{sku}: price_lyd must be greater than zero")

		if product["type"] == "variable":
			variants = product.get("variants") or []
			if not variants:
				raise SeedDataError(f"{sku}: a variable product needs variants")
			for variant in variants:
				if not variant.get("sku") or not variant.get("size"):
					raise SeedDataError(f"{sku}: every variant needs a sku and a size")
				if variant["sku"] in seen_skus:
					raise SeedDataError(f"{sku}: variant SKU {variant['sku']} appears twice")
				seen_skus.add(variant["sku"])
		elif product.get("variants"):
			raise SeedDataError(f"{sku}: only a variable product may have variants")

	for product in products:
		for component in product.get("bundle_components") or []:
			if component not in seen_skus:
				raise SeedDataError(f"{product['sku']}: bundle component {component} is not in this file")


def warnings(products: list[dict]) -> list[str]:
	"""Things worth saying out loud that are not bad enough to refuse the file."""
	notes: list[str] = []
	stock = {p["sku"]: p.get("stock") for p in products}

	for product in products:
		components = product.get("bundle_components") or []
		if not components:
			continue
		# A bundle can only be assembled as often as its scarcest part allows.
		limits = [stock.get(c) for c in components if isinstance(stock.get(c), int)]
		possible = min(limits) if limits else None
		claimed = product.get("stock")
		if possible is not None and isinstance(claimed, int) and claimed > possible:
			notes.append(
				f"{product['sku']}: stock says {claimed}, but its components allow only {possible} "
				f"({', '.join(components)}). ERPNext holds the components' stock, not the bundle's."
			)

	for product in products:
		if product["type"] != "variable" and product.get("stock") is None:
			notes.append(f"{product['sku']}: no stock given, so it starts with none")

	return notes
