"""Image embedder interface.

An embedder turns an image into a unit-length vector. Search compares vectors only within one model
(`name`), because two models' vectors mean nothing to each other — `services.image_search` stores the
name alongside every vector and refuses to mix them.
"""

from abc import ABC, abstractmethod


class ImageEmbedder(ABC):
	code: str = ""

	@property
	@abstractmethod
	def name(self) -> str:
		"""Stable identifier of the model, stored with every vector it produces."""

	@property
	@abstractmethod
	def dimensions(self) -> int:
		"""Length of the vectors this embedder returns."""

	@abstractmethod
	def embed(self, image_bytes: bytes) -> list[float]:
		"""Encode one image. Returns a unit-length vector, or raises EmbeddingError."""

	def is_available(self) -> bool:
		"""False when the model or its runtime is missing, so search can say so instead of erroring."""
		return True


class EmbeddingError(RuntimeError):
	"""The image could not be encoded (not an image, corrupt, or the model failed)."""
