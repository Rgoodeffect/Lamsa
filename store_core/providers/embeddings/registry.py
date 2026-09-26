import frappe

from store_core.providers.base_registry import ProviderRegistry
from store_core.providers.embeddings.base import ImageEmbedder

registry = ProviderRegistry("lamsa_image_embedders", "image embedder")


def get_embedder(code: str | None = None) -> ImageEmbedder:
	code = code or frappe.get_cached_doc("Lamsa Settings").image_embedder or "clip_onnx"
	return registry.get(code)


def is_available(code: str | None = None) -> bool:
	"""Whether image search can run at all: the model and its runtime are both present."""
	try:
		return get_embedder(code).is_available()
	except Exception:
		return False
