"""Product feed rows for Meta Commerce Manager (Facebook / Instagram Shops).

One row per sellable variant (or per simple item), grouped by `item_group_id` so Meta shows the
variants as one product with size/colour options. The storefront turns these rows into CSV or
RSS/XML at /feeds/meta.csv and /feeds/meta.xml and adds absolute `link` / `image_link` URLs.
"""

import re

from frappe.utils import flt

from store_core.services import catalog

_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def plain(html: str | None, limit: int = 5000) -> str:
	text = _SPACES.sub(" ", _TAGS.sub(" ", html or "").replace("&nbsp;", " ")).strip()
	return text[:limit]


def feed_rows(index: dict | None = None) -> list[dict]:
	index = index or catalog.get_index()
	currency = index["currency"]
	groups = index["groups"]
	rows = []
	for p in index["products"]:
		group = groups.get(p["group"]) or {}
		product_type = " > ".join(b["title"] for b in catalog.breadcrumbs(index, p["group"]))
		is_kids = bool(p["age_range"] or group.get("has_age_filter") or _in_kids_tree(index, p["group"]))
		base = {
			"item_group_id": p["code"],
			"title": p["name"],
			"description": plain(p["description"]) or p["name"],
			"condition": "new",
			"slug": p["slug"],
			"brand": p["brand"] or "Lamsa",
			"product_type": product_type,
			"age_group": "kids" if is_kids else "adult",
			# only when known: Meta treats gender as optional; kids items default to unisex
			"gender": p["gender"] or ("unisex" if is_kids else ""),
		}
		variants = p["variants"] if p["has_variants"] else [None]
		for v in variants:
			images = [i for i in ([v["image"]] if v and v["image"] else []) + p["images"] if i]
			in_stock = v["in_stock"] if v else p["in_stock"]
			price = v["price"] if v else p["min_price"]
			rows.append(
				{
					**base,
					"id": v["code"] if v else p["code"],
					"availability": "in stock" if in_stock else "out of stock",
					"price": f"{flt(price):.2f} {currency}",
					"image_link": images[0] if images else "",
					"additional_image_link": ",".join(images[1:10]),
					"size": (v or {}).get("size") or "",
					"color": (v or {}).get("color") or "",
				}
			)
	return rows


def _in_kids_tree(index: dict, group_name: str) -> bool:
	groups = index["groups"]
	g = groups.get(group_name)
	while g:
		if g.get("has_age_filter"):
			return True
		g = groups.get(g["parent"])
	return False
