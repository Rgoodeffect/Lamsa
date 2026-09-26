"""Vector maths for image search (pure Python, unit tested without a model or a bench).

Vectors are stored already normalised to unit length, so cosine similarity is just a dot product and
ranking never has to divide. Keeping this module free of frappe and of numpy means the ranking rules
— what counts as a match, how ties break, how a query with no good match is reported — can be tested
directly, which is where the behaviour customers actually notice lives.
"""

from math import sqrt

#: Below this cosine similarity a result is not shown at all. CLIP-style embeddings put genuinely
#: different products around 0.5-0.7, so a threshold in the low 0.7s keeps "no match" honest instead
#: of returning an unrelated dress. Tune per model, in Lamsa Settings.
DEFAULT_MIN_SIMILARITY = 0.75


class DimensionMismatch(ValueError):
	"""Vectors from different models, or a corrupted row: never comparable."""


def normalise(vector: list[float]) -> list[float]:
	"""Scale to unit length. A zero vector stays zero: it can then never match anything."""
	magnitude = sqrt(sum(float(v) * float(v) for v in vector))
	if magnitude == 0:
		return [0.0] * len(vector)
	return [float(v) / magnitude for v in vector]


def dot(a: list[float], b: list[float]) -> float:
	if len(a) != len(b):
		raise DimensionMismatch(f"{len(a)} != {len(b)}")
	return sum(x * y for x, y in zip(a, b, strict=True))


def similarity(a: list[float], b: list[float]) -> float:
	"""Cosine similarity of two unit vectors, clamped to [-1, 1] against rounding drift."""
	return max(-1.0, min(1.0, dot(a, b)))


def rank(
	query: list[float],
	candidates: list[dict],
	limit: int = 24,
	min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[dict]:
	"""Best matches for `query`, one row per item.

	`candidates` are {"item_code", "vector"} rows — several per product, because a product has several
	images. A product is scored by its *best* image: a customer photographing the back of a dress
	should still find it, and averaging over images would bury it.

	Returns [{"item_code", "score"}] sorted by score, best first, with anything below
	`min_similarity` left out entirely rather than padded in to fill the page.
	"""
	best: dict[str, float] = {}
	for row in candidates:
		vector = row.get("vector") or []
		if not vector:
			continue
		score = similarity(query, vector)
		code = row["item_code"]
		if score > best.get(code, -1.0):
			best[code] = score

	matches = [{"item_code": code, "score": score} for code, score in best.items() if score >= min_similarity]
	# Score first; item code second so equal scores come out in a stable order.
	matches.sort(key=lambda m: (-m["score"], m["item_code"]))
	return matches[: max(1, int(limit))]
