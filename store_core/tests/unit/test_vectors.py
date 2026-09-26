"""Image-search ranking rules (pure Python): `python -m pytest store_core/tests/unit`.

These are the rules a customer notices: which product comes first, whether a product with several
photos is found from any of them, and whether an unrelated photo honestly returns nothing.
"""

import unittest
from math import sqrt

from store_core.services import vectors as v


def unit(*values: float) -> list[float]:
	return v.normalise(list(values))


class TestNormalise(unittest.TestCase):
	def test_unit_length(self):
		result = v.normalise([3.0, 4.0])
		self.assertAlmostEqual(sqrt(sum(x * x for x in result)), 1.0)
		self.assertAlmostEqual(result[0], 0.6)
		self.assertAlmostEqual(result[1], 0.8)

	def test_already_normalised_is_unchanged(self):
		for x, y in zip(v.normalise([1.0, 0.0]), [1.0, 0.0], strict=True):
			self.assertAlmostEqual(x, y)

	def test_zero_vector_stays_zero_and_matches_nothing(self):
		zero = v.normalise([0.0, 0.0, 0.0])
		self.assertEqual(zero, [0.0, 0.0, 0.0])
		self.assertAlmostEqual(v.similarity(zero, unit(1, 1, 1)), 0.0)


class TestSimilarity(unittest.TestCase):
	def test_identical_vectors_score_one(self):
		a = unit(0.2, 0.9, -0.3)
		self.assertAlmostEqual(v.similarity(a, a), 1.0)

	def test_orthogonal_scores_zero(self):
		self.assertAlmostEqual(v.similarity(unit(1, 0), unit(0, 1)), 0.0)

	def test_opposite_scores_minus_one(self):
		self.assertAlmostEqual(v.similarity(unit(1, 0), unit(-1, 0)), -1.0)

	def test_stays_within_range_despite_rounding(self):
		a = [1.0000001, 0.0]
		self.assertLessEqual(v.similarity(a, a), 1.0)

	def test_different_dimensions_are_refused_rather_than_compared(self):
		with self.assertRaises(v.DimensionMismatch):
			v.similarity([1.0, 0.0], [1.0, 0.0, 0.0])


class TestRank(unittest.TestCase):
	def rows(self):
		return [
			{"item_code": "DRESS", "vector": unit(1, 0, 0)},
			{"item_code": "BAG", "vector": unit(0, 1, 0)},
			{"item_code": "SHOE", "vector": unit(0, 0, 1)},
		]

	def test_the_closest_product_comes_first(self):
		result = v.rank(unit(0.9, 0.1, 0), self.rows(), min_similarity=0.0)
		self.assertEqual(result[0]["item_code"], "DRESS")

	def test_a_product_is_scored_by_its_best_image(self):
		rows = [
			{"item_code": "DRESS", "vector": unit(0, 1, 0)},  # a bad angle
			{"item_code": "DRESS", "vector": unit(1, 0, 0)},  # the photo that matches
			{"item_code": "BAG", "vector": unit(0.7, 0.7, 0)},
		]
		result = v.rank(unit(1, 0, 0), rows, min_similarity=0.0)
		self.assertEqual(result[0]["item_code"], "DRESS")
		self.assertAlmostEqual(result[0]["score"], 1.0)
		# one row per product, not one per image
		self.assertEqual([m["item_code"] for m in result].count("DRESS"), 1)

	def test_a_photo_of_something_else_returns_nothing(self):
		result = v.rank(unit(0, 0, 1), [{"item_code": "DRESS", "vector": unit(1, 0, 0)}])
		self.assertEqual(result, [])

	def test_the_threshold_is_inclusive(self):
		rows = [{"item_code": "DRESS", "vector": unit(1, 0)}]
		self.assertEqual(len(v.rank(unit(1, 0), rows, min_similarity=1.0)), 1)

	def test_limit_caps_the_page(self):
		rows = [{"item_code": f"P{i}", "vector": unit(1, 0)} for i in range(10)]
		self.assertEqual(len(v.rank(unit(1, 0), rows, limit=3, min_similarity=0.0)), 3)

	def test_equal_scores_come_out_in_a_stable_order(self):
		rows = [
			{"item_code": "ZEBRA", "vector": unit(1, 0)},
			{"item_code": "ALPHA", "vector": unit(1, 0)},
		]
		result = v.rank(unit(1, 0), rows, min_similarity=0.0)
		self.assertEqual([m["item_code"] for m in result], ["ALPHA", "ZEBRA"])

	def test_rows_without_a_vector_are_skipped(self):
		rows = [{"item_code": "DRESS", "vector": []}, {"item_code": "BAG", "vector": unit(1, 0)}]
		result = v.rank(unit(1, 0), rows, min_similarity=0.0)
		self.assertEqual([m["item_code"] for m in result], ["BAG"])

	def test_empty_catalog_returns_nothing(self):
		self.assertEqual(v.rank(unit(1, 0), []), [])
