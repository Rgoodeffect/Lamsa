"""Pure-Python unit tests (no bench needed): `python -m pytest store_core/tests/unit`.

Also collected by `bench run-tests --app store_core` because they are unittest.TestCase classes.
"""

import json
import unittest
from itertools import pairwise
from pathlib import Path

from store_core.providers.notifications import templates
from store_core.utils import status_machine as sm
from store_core.utils.phone import InvalidPhone, local_format, normalize_libyan_phone, whatsapp_number
from store_core.utils.slug import slugify

CASES = json.loads((Path(__file__).parent / "phone_cases.json").read_text(encoding="utf-8"))


class TestLibyanPhone(unittest.TestCase):
	def test_valid_numbers_normalize_to_e164(self):
		for raw, expected in CASES["valid"]:
			with self.subTest(raw=raw):
				self.assertEqual(normalize_libyan_phone(raw), expected)

	def test_invalid_numbers_raise(self):
		for raw in CASES["invalid"]:
			with self.subTest(raw=raw):
				with self.assertRaises(InvalidPhone):
					normalize_libyan_phone(raw)

	def test_display_formats(self):
		self.assertEqual(local_format("+218912345678"), "091 234 5678")
		self.assertEqual(whatsapp_number("+218912345678"), "218912345678")


class TestStatusMachine(unittest.TestCase):
	def test_happy_path(self):
		path = [sm.NEW, sm.CONFIRMED, sm.OUT_FOR_DELIVERY, sm.DELIVERED]
		for current, target in pairwise(path):
			sm.assert_transition(current, target)

	def test_rejected_transitions(self):
		for current, target in [
			(sm.NEW, sm.DELIVERED),
			(sm.NEW, sm.OUT_FOR_DELIVERY),
			(sm.OUT_FOR_DELIVERY, sm.CANCELLED),
			(sm.DELIVERED, sm.RETURNED),
			(sm.CANCELLED, sm.NEW),
			("Bogus", sm.NEW),
		]:
			with self.subTest(current=current, target=target):
				with self.assertRaises(sm.InvalidTransition):
					sm.assert_transition(current, target)

	def test_same_status_is_noop(self):
		sm.assert_transition(sm.DELIVERED, sm.DELIVERED)

	def test_agent_transitions(self):
		self.assertTrue(sm.is_agent_transition(sm.OUT_FOR_DELIVERY, sm.DELIVERED))
		self.assertTrue(sm.is_agent_transition(sm.OUT_FOR_DELIVERY, sm.RETURNED))
		self.assertFalse(sm.is_agent_transition(sm.NEW, sm.CONFIRMED))

	def test_next_statuses(self):
		self.assertEqual(sm.next_statuses(sm.NEW), [sm.CONFIRMED, sm.CANCELLED])
		self.assertEqual(sm.next_statuses(sm.DELIVERED), [])


class TestSlug(unittest.TestCase):
	def test_arabic_and_latin(self):
		self.assertEqual(slugify("فستان سهرة مطرّز"), "فستان-سهرة-مطرز")
		self.assertEqual(slugify("  Kids' T-Shirt (Blue)  "), "kids-t-shirt-blue")
		self.assertEqual(slugify("هدايا_ومناسبات"), "هدايا-ومناسبات")
		self.assertEqual(slugify(""), "")
		self.assertLessEqual(len(slugify("ا" * 200)), 80)


class TestNotificationTemplates(unittest.TestCase):
	"""templates.py is pure Python, so it belongs here: importing it is what catches a syntax error.

	It had none of this coverage before, which is how `except KeyError, IndexError:` (Python 2
	syntax) shipped: nothing imported the module outside a running bench.
	"""

	def test_every_template_renders_with_the_full_context(self):
		context = {
			"customer_name": "سارة",
			"order_no": "L-00042",
			"grand_total": "250.00",
			"currency": "د.ل",
			"eta": "2-3 أيام",
			"coupon_code": "LAMSAAB12CD",
			"coupon_percent": "10",
			"coupon_valid_upto": "2026-10-26",
		}
		for name in templates.TEMPLATES:
			with self.subTest(template=name):
				text = templates.render(name, context)
				self.assertTrue(text)
				self.assertNotIn("{", text)

	def test_missing_placeholder_returns_the_raw_template(self):
		text = templates.render("order_placed", {})
		self.assertEqual(text, templates.TEMPLATES["order_placed"])

	def test_unknown_template_is_empty(self):
		self.assertEqual(templates.render("no_such_template", {}), "")

	def test_every_status_has_a_message(self):
		"""Every status a customer can be told about maps to a template that exists."""
		for status in sm.STATUSES:
			if status == sm.NEW:  # a new order gets "order_placed" instead
				continue
			with self.subTest(status=status):
				self.assertIn(status, templates.STATUS_TEMPLATES)
				self.assertIn(templates.STATUS_TEMPLATES[status], templates.TEMPLATES)
