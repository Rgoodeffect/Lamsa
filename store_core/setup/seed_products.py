"""Import the initial catalog from data/products.seed.json into ERPNext.

Run it from the bench (dry run first, always):

    bench --site <site> execute store_core.setup.seed_products.run --kwargs "{'dry_run': True}"
    bench --site <site> execute store_core.setup.seed_products.run

Idempotent by SKU: every product, variant, category, price and stock entry is an upsert, so running
it twice creates nothing twice. The plan (what would change) is computed by `seed_plan`, which is
pure Python and unit tested; this module is only the part that talks to ERPNext, kept deliberately
thin so the risky logic lives where a bench is not needed to test it.

Nothing is published: the goods have not arrived and the storefront has no pre-order path, so every
item is created with `lamsa_publish = 0`. The store manager flips that in the desk when stock lands.

Images: a branded placeholder is generated per SKU into `data/product-images/<sku>/main.png` and
attached as the item's image. To use a real photo later, drop `main.jpg` (then `2.jpg`, `3.jpg`, …)
into the same folder and re-run: the importer re-attaches whatever `main.*` it finds.
"""

import json
import os

import frappe
from frappe.utils import flt

from store_core.setup import seed_plan
from store_core.setup.seed_images import ensure_placeholder, find_images

DEFAULT_SEED_FILE = "data/products.seed.json"
SIZE_ATTRIBUTE = seed_plan.SIZE_ATTRIBUTE


def run(dry_run: bool = False, seed_file: str | None = None, company: str | None = None):
	"""Import the catalog. Pass dry_run=True to print the plan without writing anything."""
	settings = frappe.get_cached_doc("Lamsa Settings")
	company = company or settings.company
	warehouse = settings.warehouse
	price_list = settings.selling_price_list
	path = _resolve(seed_file or DEFAULT_SEED_FILE)

	products = seed_plan.load(path)
	plan = seed_plan.build_plan(products)

	log = _Log(dry_run)
	log.header(f"Seeding {len(products)} products from {path}")
	log.header(f"company={company}  warehouse={warehouse}  price_list={price_list}")
	for warning in plan["warnings"]:
		log.warn(warning)

	# 1. size attribute values, so variants can reference them
	_ensure_size_attribute(plan["size_values"], log)

	# 2. categories
	for category in plan["categories"]:
		_upsert_category(category, log)

	# 3. items (templates, variants, sellables) — templates before their variants, which build_plan
	#    already guarantees by ordering a template ahead of its variants
	for item in plan["items"]:
		_upsert_item(item, company, log)

	# 4. prices, on sellable codes only
	for price in plan["prices"]:
		_upsert_price(price, price_list, log)

	# 5. stock, as an opening balance in the store warehouse
	for item in plan["items"]:
		if item.get("stock") is not None:
			_set_opening_stock(item["item_code"], flt(item["stock"]), company, warehouse, log)

	# 6. product bundles
	for bundle in plan["bundles"]:
		_upsert_bundle(bundle, log)

	# 7. placeholder images
	for item in plan["items"]:
		if item["role"] != "variant":
			_attach_images(item, log)

	if not dry_run:
		frappe.db.commit()
	log.summary()
	return log.as_dict()


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------


def _ensure_size_attribute(sizes: list[str], log):
	if not sizes:
		return
	if not frappe.db.exists("Item Attribute", SIZE_ATTRIBUTE):
		log.act("create", "Item Attribute", SIZE_ATTRIBUTE)
		if not log.dry_run:
			frappe.get_doc(
				{"doctype": "Item Attribute", "attribute_name": SIZE_ATTRIBUTE, "item_attribute_values": []}
			).insert(ignore_permissions=True)

	if log.dry_run:
		return
	attr = frappe.get_doc("Item Attribute", SIZE_ATTRIBUTE)
	present = {row.attribute_value for row in attr.item_attribute_values}
	changed = False
	for size in sizes:
		if size not in present:
			attr.append("item_attribute_values", {"attribute_value": size, "abbr": _abbr(size)})
			changed = True
			log.act("add value", "Item Attribute", f"{SIZE_ATTRIBUTE}: {size}")
	if changed:
		attr.flags.ignore_permissions = True
		attr.save()


def _upsert_category(category: dict, log):
	name = category["name"]
	parent = "All Item Groups"
	if frappe.db.exists("Item Group", name):
		if not log.dry_run:
			doc = frappe.get_doc("Item Group", name)
			doc.lamsa_show_in_store = 1
			doc.lamsa_slug = category["slug"]
			doc.lamsa_title_ar = category["title_ar"]
			doc.lamsa_sort = category["sort"]
			doc.flags.ignore_permissions = True
			doc.save()
		log.act("update", "Item Group", name)
		return
	log.act("create", "Item Group", name)
	if not log.dry_run:
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": parent,
				"is_group": 0,
				"lamsa_show_in_store": 1,
				"lamsa_slug": category["slug"],
				"lamsa_title_ar": category["title_ar"],
				"lamsa_sort": category["sort"],
			}
		).insert(ignore_permissions=True)


def _upsert_item(item: dict, company: str, log):
	code = item["item_code"]
	exists = frappe.db.exists("Item", code)
	log.act("update" if exists else "create", "Item", f"{code}  ({item['item_name']})")
	if log.dry_run:
		return

	doc = frappe.get_doc("Item", code) if exists else frappe.new_doc("Item")
	if not exists:
		doc.item_code = code
		doc.item_group = item["item_group"]
		doc.stock_uom = "Nos"
	doc.item_name = item["item_name"][:140]
	doc.has_variants = item.get("has_variants", 0)
	doc.is_stock_item = item.get("is_stock_item", 1)
	doc.is_sales_item = 1
	doc.is_purchase_item = 0 if item.get("role") == "template" else 1
	doc.include_item_in_manufacturing = 0
	if item.get("weight_g"):
		doc.weight_per_unit = flt(item["weight_g"])
		doc.weight_uom = "Gram"

	# variant wiring
	if item.get("role") == "variant":
		doc.variant_of = item["variant_of"]
		doc.item_group = item["item_group"]
		_set_variant_attributes(doc, item["attributes"])
	elif item.get("has_variants"):
		_set_template_attributes(doc, [SIZE_ATTRIBUTE])

	# Lamsa fields
	if item.get("role") != "variant":
		doc.lamsa_slug = item.get("slug") or ""
		doc.lamsa_name_en = item.get("name_en") or ""
		doc.lamsa_short_description_ar = item.get("short_description_ar") or ""
		doc.lamsa_description_ar = item.get("description_ar") or ""
		doc.lamsa_featured = item.get("featured", 0)
		doc.lamsa_publish = item.get("publish", 0)
		# internal, permlevel-1 fields
		if item.get("cost_usd") is not None:
			doc.lamsa_cost_usd = flt(item["cost_usd"])
		doc.lamsa_supplier_url = item.get("supplier_url") or ""

	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()

	_set_tags(doc, item.get("tags") or [])
	if item.get("note_internal"):
		_add_internal_note(code, item["note_internal"])
	if item.get("supplier"):
		_link_supplier(doc, item["supplier"])


def _set_variant_attributes(doc, attributes: dict):
	doc.set("attributes", [])
	for name, value in attributes.items():
		doc.append("attributes", {"attribute": name, "attribute_value": value})


def _set_template_attributes(doc, names: list[str]):
	existing = {row.attribute for row in doc.get("attributes", [])}
	for name in names:
		if name not in existing:
			doc.append("attributes", {"attribute": name})


def _upsert_price(price: dict, price_list: str, log):
	code = price["item_code"]
	rate = flt(price["rate"])
	existing = frappe.db.get_value(
		"Item Price", {"item_code": code, "price_list": price_list, "selling": 1}, "name"
	)
	log.act("update" if existing else "create", "Item Price", f"{code} = {rate} LYD")
	if log.dry_run:
		return
	if existing:
		frappe.db.set_value("Item Price", existing, "price_list_rate", rate)
	else:
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": code,
				"price_list": price_list,
				"selling": 1,
				"price_list_rate": rate,
				"currency": "LYD",
			}
		).insert(ignore_permissions=True)


def _set_opening_stock(code: str, qty: float, company: str, warehouse: str, log):
	"""Set the warehouse balance to `qty` via a Stock Reconciliation. Idempotent: it targets an
	absolute quantity, so re-running does not stack the stock up."""
	current = flt(frappe.db.get_value("Bin", {"item_code": code, "warehouse": warehouse}, "actual_qty"))
	if abs(current - qty) < 0.001:
		return  # already at the target
	log.act("stock", "Item", f"{code}: {current} -> {qty} @ {warehouse}")
	if log.dry_run:
		return
	rate = flt(frappe.db.get_value("Item Price", {"item_code": code, "selling": 1}, "price_list_rate"))
	recon = frappe.new_doc("Stock Reconciliation")
	recon.company = company
	recon.purpose = "Stock Reconciliation"
	recon.append(
		"items",
		{"item_code": code, "warehouse": warehouse, "qty": qty, "valuation_rate": rate or 1},
	)
	recon.flags.ignore_permissions = True
	recon.flags.ignore_mandatory = True
	recon.save()
	recon.submit()


def _upsert_bundle(bundle: dict, log):
	sku = bundle["sku"]
	components = bundle["components"]
	log.act("bundle", "Product Bundle", f"{sku} = {', '.join(components)}")
	if log.dry_run:
		return
	if frappe.db.exists("Product Bundle", {"new_item_code": sku}):
		doc = frappe.get_doc("Product Bundle", {"new_item_code": sku})
		doc.set("items", [])
	else:
		doc = frappe.new_doc("Product Bundle")
		doc.new_item_code = sku
	for component in components:
		doc.append("items", {"item_code": component, "qty": 1})
	doc.flags.ignore_permissions = True
	doc.save()


# ---------------------------------------------------------------------------
# Odds and ends
# ---------------------------------------------------------------------------


def _attach_images(item: dict, log):
	code = item["item_code"]
	folder = _images_dir(code)
	images = find_images(folder)
	if not images:
		placeholder = ensure_placeholder(folder, item["item_name"])
		images = [placeholder] if placeholder else []
	if not images:
		return
	main = images[0]
	log.act("image", "Item", f"{code} <- {os.path.basename(main)}")
	if log.dry_run:
		return
	file_url = _upload_file(main, code)
	if file_url:
		frappe.db.set_value("Item", code, "image", file_url)


def _upload_file(path: str, code: str) -> str | None:
	filename = f"{code}-{os.path.basename(path)}"
	if frappe.db.exists("File", {"attached_to_doctype": "Item", "attached_to_name": code, "file_name": filename}):
		return frappe.db.get_value("File", {"attached_to_name": code, "file_name": filename}, "file_url")
	with open(path, "rb") as f:
		content = f.read()
	saved = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"attached_to_doctype": "Item",
			"attached_to_name": code,
			"is_private": 0,
			"content": content,
		}
	)
	saved.flags.ignore_permissions = True
	saved.insert()
	return saved.file_url


def _set_tags(doc, tags: list[str]):
	for tag in tags:
		try:
			frappe.get_doc("Item", doc.name).add_tag(tag) if hasattr(doc, "add_tag") else None
		except Exception:
			pass
	# frappe's tag API differs across versions; fall back to the tag utility
	if tags:
		try:
			from frappe.desk.doctype.tag.tag import add_tags

			add_tags(",".join(tags), "Item", [doc.name])
		except Exception:
			pass


def _add_internal_note(code: str, note: str):
	doc = frappe.get_doc("Item", code)
	existing = frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Item", "reference_name": code, "comment_type": "Comment"},
		fields=["content"],
	)
	if any(note in (c.content or "") for c in existing):
		return
	doc.add_comment("Comment", f"[Internal] {note}")


def _link_supplier(doc, supplier_name: str):
	name = supplier_name.strip()[:140]
	if not name:
		return
	if not frappe.db.exists("Supplier", name):
		try:
			frappe.get_doc(
				{"doctype": "Supplier", "supplier_name": name, "supplier_group": _default_supplier_group()}
			).insert(ignore_permissions=True)
		except Exception:
			return
	if not any(row.supplier == name for row in doc.get("supplier_items", [])):
		doc.append("supplier_items", {"supplier": name})
		doc.flags.ignore_permissions = True
		doc.save()


def _default_supplier_group() -> str:
	for candidate in ("All Supplier Groups", "Local", "Services"):
		if frappe.db.exists("Supplier Group", candidate):
			return candidate
	group = frappe.get_all("Supplier Group", filters={"is_group": 0}, limit=1)
	return group[0].name if group else "All Supplier Groups"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _abbr(size: str) -> str:
	cleaned = "".join(ch for ch in size if ch.isalnum())
	return (cleaned[:6] or "SZ").upper()


def _resolve(path: str) -> str:
	if os.path.isabs(path):
		return path
	return os.path.join(frappe.get_app_path("store_core", ".."), path)


def _images_dir(code: str) -> str:
	return os.path.join(frappe.get_app_path("store_core", ".."), "data", "product-images", code)


class _Log:
	def __init__(self, dry_run: bool):
		self.dry_run = dry_run
		self.actions: list[dict] = []

	def header(self, text: str):
		print(f"  {text}")

	def warn(self, text: str):
		print(f"  ⚠ {text}")
		self.actions.append({"kind": "warning", "text": text})

	def act(self, action: str, doctype: str, detail: str):
		prefix = "WOULD " if self.dry_run else ""
		print(f"  {prefix}{action:9s} {doctype:14s} {detail}")
		self.actions.append({"kind": action, "doctype": doctype, "detail": detail})

	def summary(self):
		verb = "planned" if self.dry_run else "applied"
		counts: dict[str, int] = {}
		for a in self.actions:
			counts[a["kind"]] = counts.get(a["kind"], 0) + 1
		print(f"\n  {verb}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

	def as_dict(self) -> dict:
		return {"dry_run": self.dry_run, "actions": self.actions}
