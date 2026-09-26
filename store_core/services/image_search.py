"""Search the catalog by image.

A customer uploads or pastes a photo; the store shows the products that look like it.

How it works: every published product image is encoded once into a unit vector (a background job, so
an image upload never waits for a model) and stored as a **Lamsa Image Embedding**. A search encodes
the customer's photo the same way and ranks the stored vectors by cosine similarity
(`services.vectors`). A product is scored by its closest image, and anything below the similarity
threshold is left out rather than padded in, so an unrelated photo honestly returns nothing.

The photo is encoded in this process and discarded; it is never stored and never leaves the server.

Vectors are only ever compared within one model: every row records which embedder produced it, and
changing the model simply orphans the old rows until they are rebuilt.
"""

import json

import frappe
from frappe.utils import cint, flt

from store_core.providers.embeddings.base import EmbeddingError
from store_core.providers.embeddings.registry import get_embedder, is_available
from store_core.services import catalog, vectors
from store_core.services.orders import CheckoutError
from store_core.services.settings import get_settings

INDEX_CACHE_KEY = "lamsa:image_index:v1"
INDEX_TTL_SECONDS = 600
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_RESULTS = 24
DOCTYPE = "Lamsa Image Embedding"


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def search(image_bytes: bytes, limit: int = 12) -> dict:
	"""Products that look like this image, as storefront product cards."""
	if not image_bytes:
		raise CheckoutError("image_required")
	if len(image_bytes) > MAX_UPLOAD_BYTES:
		raise CheckoutError("image_too_large", max_bytes=MAX_UPLOAD_BYTES)
	if not is_available():
		raise CheckoutError("image_search_unavailable")

	embedder = get_embedder()
	try:
		query = embedder.embed(image_bytes)
	except EmbeddingError as exc:
		# A file that is not an image is the customer's mistake; a model failure is ours. Both leave
		# the shopper with a usable message, and the detail goes to the Error Log.
		frappe.log_error(title="Lamsa image search: could not encode the uploaded image", message=str(exc))
		raise CheckoutError("image_unreadable")

	rows = _index(embedder.name)
	if not rows:
		return {"products": [], "matched": 0, "indexed": 0}

	settings = get_settings()
	threshold = flt(settings.image_search_min_similarity) or vectors.DEFAULT_MIN_SIMILARITY
	limit = max(1, min(cint(limit) or 12, MAX_RESULTS))
	try:
		matches = vectors.rank(query, rows, limit=limit, min_similarity=threshold)
	except vectors.DimensionMismatch:
		# Stored vectors no longer match the model's output: the index needs rebuilding.
		frappe.log_error(title="Lamsa image search: stored vectors do not match the model")
		raise CheckoutError("image_search_unavailable")

	index = catalog.get_index()
	products = []
	for match in matches:
		product = _find_by_code(index, match["item_code"])
		if product:
			card = catalog.product_card(product)
			card["score"] = round(match["score"], 4)
			products.append(card)
	return {"products": products, "matched": len(products), "indexed": len(rows)}


def _find_by_code(index: dict, item_code: str) -> dict | None:
	"""Embeddings are stored per template item, which is what the storefront lists."""
	for product in index["products"]:
		if product["code"] == item_code:
			return product
	return None


def _index(model: str) -> list[dict]:
	"""Every stored vector for this model, cached like the catalog index."""
	cached = frappe.cache.get_value(INDEX_CACHE_KEY)
	if cached and cached.get("model") == model:
		return cached["rows"]
	rows = [
		{"item_code": row.item_code, "vector": json.loads(row.vector or "[]")}
		for row in frappe.get_all(
			DOCTYPE, filters={"model": model}, fields=["item_code", "vector"], limit_page_length=0
		)
	]
	frappe.cache.set_value(INDEX_CACHE_KEY, {"model": model, "rows": rows}, expires_in_sec=INDEX_TTL_SECONDS)
	return rows


def invalidate_index():
	frappe.cache.delete_value(INDEX_CACHE_KEY)


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------


def reindex_item(item_code: str):
	"""Re-encode one published product's images. Safe to call repeatedly."""
	if not is_available():
		return
	embedder = get_embedder()
	wanted = _image_urls(item_code)
	existing = {
		row.file_url: row.name
		for row in frappe.get_all(
			DOCTYPE, filters={"item_code": item_code, "model": embedder.name}, fields=["name", "file_url"]
		)
	}

	for url in wanted:
		if url in existing:
			continue  # already encoded by this model
		content = _read_image(url)
		if content is None:
			continue
		try:
			vector = embedder.embed(content)
		except EmbeddingError as exc:
			frappe.log_error(title=f"Lamsa image search: could not encode {url}", message=str(exc))
			continue
		frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"item_code": item_code,
				"file_url": url,
				"model": embedder.name,
				"dimensions": len(vector),
				"vector": json.dumps(vector),
			}
		).insert(ignore_permissions=True)

	# Images that are no longer on the product, and vectors from other models, are dropped.
	for url, name in existing.items():
		if url not in wanted:
			frappe.delete_doc(DOCTYPE, name, ignore_permissions=True, force=True)
	invalidate_index()


def reindex_all():
	"""Encode every published product. Run once after installing the model:

	    bench --site <site> execute store_core.services.image_search.reindex_all
	"""
	if not is_available():
		frappe.throw("Image search is not configured: set lamsa_image_model_path and install onnxruntime")
	index = catalog.get_index()
	for product in index["products"]:
		reindex_item(product["code"])
	frappe.db.commit()


def on_item_change(doc, method=None):
	"""Queue a re-encode when a published product's images may have changed."""
	if not cint(getattr(doc, "lamsa_publish", 0)):
		return
	frappe.enqueue(
		"store_core.services.image_search.reindex_item",
		queue="long",
		job_id=f"lamsa-image-reindex-{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
		item_code=doc.name,
	)


def _image_urls(item_code: str) -> list[str]:
	"""The product's own image plus its public image attachments, in display order."""
	index = catalog.get_index()
	product = _find_by_code(index, item_code)
	if not product:
		return []
	return [url for url in product["images"] if url][:10]


def _read_image(file_url: str) -> bytes | None:
	from frappe.utils.file_manager import get_file

	try:
		return get_file(file_url)[1]
	except Exception:
		frappe.log_error(title=f"Lamsa image search: could not read {file_url}")
		return None
