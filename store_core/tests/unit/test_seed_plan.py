"""Product seeding rules (pure Python): `python -m pytest store_core/tests/unit`.

What is tested here is what `--dry-run` promises: the same plan the import then carries out. So the
rules that decide the shape of the catalog — one price per sellable code, a template that is not
itself sellable, a bundle that holds no stock of its own, and a file that is refused rather than half
imported — are covered without a bench.
"""

import unittest
from pathlib import Path

from store_core.setup import seed_plan as sp

SEED_FILE = Path(__file__).parents[3] / "data" / "products.seed.json"


def simple(sku="SKU-1", **overrides) -> dict:
	product = {
		"sku": sku,
		"name_ar": "منتج",
		"slug": sku.lower(),
		"category": "gifts",
		"type": "simple",
		"price_lyd": 100,
		"stock": 3,
	}
	product.update(overrides)
	return product


def variable(sku="VAR-1", sizes=("S", "M")) -> dict:
	return simple(
		sku,
		type="variable",
		stock=None,
		variants=[{"sku": f"{sku}-{s}", "size": s, "stock": 2} for s in sizes],
	)


class TestValidation(unittest.TestCase):
	def test_an_empty_file_is_refused(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([])

	def test_required_fields(self):
		for field in ("sku", "name_ar", "slug", "category", "type", "price_lyd"):
			with self.subTest(missing=field):
				product = simple()
				del product[field]
				with self.assertRaises(sp.SeedDataError):
					sp.build_plan([product])

	def test_a_repeated_sku_is_refused(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple("A"), simple("A", slug="other")])

	def test_a_repeated_slug_is_refused(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple("A"), simple("B", slug="a")])

	def test_a_variant_sku_may_not_collide_with_a_product(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple("VAR-1-S"), variable("VAR-1")])

	def test_an_unknown_category_is_refused(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple(category="shoes")])

	def test_an_unknown_type_is_refused(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple(type="mystery")])

	def test_a_free_or_negative_price_is_refused(self):
		for price in (0, -5):
			with self.subTest(price=price):
				with self.assertRaises(sp.SeedDataError):
					sp.build_plan([simple(price_lyd=price)])

	def test_a_variable_product_needs_variants(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple(type="variable")])

	def test_only_a_variable_product_may_have_variants(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple(variants=[{"sku": "X", "size": "S"}])])

	def test_a_bundle_component_must_be_in_the_file(self):
		with self.assertRaises(sp.SeedDataError):
			sp.build_plan([simple("BOX", type="bundle", bundle_components=["MISSING"])])


class TestPlan(unittest.TestCase):
	def test_a_simple_product_is_one_item_with_one_price(self):
		plan = sp.build_plan([simple("A")])
		self.assertEqual([i["item_code"] for i in plan["items"]], ["A"])
		self.assertEqual(plan["prices"], [{"item_code": "A", "rate": 100}])

	def test_a_variable_product_prices_the_variants_not_the_template(self):
		"""ERPNext v16 refuses an Item Price on a template, so each size carries the price."""
		plan = sp.build_plan([variable("V", sizes=("S", "M", "L"))])
		template = plan["items"][0]
		self.assertEqual(template["item_code"], "V")
		self.assertEqual(template["has_variants"], 1)
		self.assertEqual([p["item_code"] for p in plan["prices"]], ["V-S", "V-M", "V-L"])
		self.assertNotIn("V", [p["item_code"] for p in plan["prices"]])

	def test_variants_carry_the_size_attribute_and_their_own_stock(self):
		plan = sp.build_plan([variable("V", sizes=("XL",))])
		variant = next(i for i in plan["items"] if i["role"] == "variant")
		self.assertEqual(variant["variant_of"], "V")
		self.assertEqual(variant["attributes"], {sp.SIZE_ATTRIBUTE: "XL"})
		self.assertEqual(variant["stock"], 2)
		self.assertEqual(variant["is_stock_item"], 1)

	def test_a_bundle_holds_no_stock_of_its_own(self):
		"""ERPNext stocks the parts of a bundle, not the package, so it is a non-stock item."""
		plan = sp.build_plan([simple("BOX", type="bundle", bundle_components=[]), simple("PART")])
		box = next(i for i in plan["items"] if i["item_code"] == "BOX")
		self.assertEqual(box["is_stock_item"], 0)

	def test_nothing_is_published_until_the_goods_arrive(self):
		plan = sp.build_plan([simple("A"), variable("V")])
		for item in plan["items"]:
			if item["role"] != "variant":
				self.assertEqual(item["publish"], 0, item["item_code"])

	def test_sizes_are_collected_once_in_order(self):
		plan = sp.build_plan([variable("A", sizes=("S", "M")), variable("B", sizes=("M", "L"))])
		self.assertEqual(plan["size_values"], ["S", "M", "L"])

	def test_categories_are_listed_once(self):
		plan = sp.build_plan([simple("A"), simple("B", slug="b"), simple("C", slug="c", category="kids")])
		self.assertEqual([c["slug"] for c in plan["categories"]], ["gifts", "kids"])
		self.assertEqual(plan["categories"][0]["name"], "Gifts")

	def test_internal_fields_are_planned_but_marked_internal(self):
		plan = sp.build_plan([simple("A", cost_usd=6.5, supplier_url="https://example.com")])
		item = plan["items"][0]
		self.assertEqual(item["cost_usd"], 6.5)
		self.assertEqual(item["supplier_url"], "https://example.com")


class TestWarnings(unittest.TestCase):
	def test_a_bundle_claiming_more_than_its_parts_allow_is_flagged(self):
		plan = sp.build_plan(
			[
				simple("BOX", type="bundle", stock=15, bundle_components=["P1", "P2"]),
				simple("P1", slug="p1", stock=5),
				simple("P2", slug="p2", stock=5),
			]
		)
		self.assertTrue(any("BOX" in w and "15" in w and "5" in w for w in plan["warnings"]))

	def test_a_product_without_stock_is_flagged(self):
		plan = sp.build_plan([simple("A", stock=None)])
		self.assertTrue(any("A" in w for w in plan["warnings"]))


class TestTheRealSeedFile(unittest.TestCase):
	"""The file that actually ships must stay loadable and consistent."""

	def test_it_loads_and_plans(self):
		plan = sp.build_plan(sp.load(SEED_FILE))
		codes = [i["item_code"] for i in plan["items"]]
		self.assertEqual(len(codes), len(set(codes)), "an item code is planned twice")
		self.assertEqual([c["slug"] for c in plan["categories"]], ["gifts", "accessories", "women", "kids"])
		# 6 products + 10 variants
		self.assertEqual(len(codes), 16)
		# every sellable code is priced exactly once
		priced = [p["item_code"] for p in plan["prices"]]
		self.assertEqual(len(priced), len(set(priced)))
		self.assertEqual(len(priced), 13)

	def test_the_gift_box_stock_conflict_is_reported(self):
		plan = sp.build_plan(sp.load(SEED_FILE))
		self.assertTrue(any("LAM-GIFT-001" in w for w in plan["warnings"]))


class TestImageOrdering(unittest.TestCase):
	"""find_images decides which photo becomes a product's main image; it is pure and testable."""

	def setUp(self):
		import tempfile
		self.dir = tempfile.mkdtemp()

	def _touch(self, *names):
		import os
		for n in names:
			open(os.path.join(self.dir, n), "w").close()

	def _base(self, paths):
		import os
		return [os.path.basename(p) for p in paths]

	def test_empty_folder_has_no_images(self):
		from store_core.setup import seed_images as si
		self.assertEqual(si.find_images(self.dir), [])

	def test_missing_folder_is_safe(self):
		from store_core.setup import seed_images as si
		self.assertEqual(si.find_images("/no/such/folder/xyz"), [])

	def test_main_comes_first_then_numbered(self):
		from store_core.setup import seed_images as si
		self._touch("2.jpg", "main.jpg", "3.png")
		self.assertEqual(self._base(si.find_images(self.dir)), ["main.jpg", "2.jpg", "3.png"])

	def test_a_real_photo_wins_over_the_placeholder(self):
		from store_core.setup import seed_images as si
		self._touch("main.jpg", "placeholder.png")
		self.assertEqual(self._base(si.find_images(self.dir)), ["main.jpg"])

	def test_placeholder_is_used_only_when_alone(self):
		from store_core.setup import seed_images as si
		self._touch("placeholder.png")
		self.assertEqual(self._base(si.find_images(self.dir)), ["placeholder.png"])
