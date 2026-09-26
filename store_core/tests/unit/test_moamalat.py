"""Moamalat SecureHash unit tests: `python -m pytest store_core/tests/unit`.

Pure Python, no bench. The expected digests are computed here from the documented algorithm with
an HMAC written out by hand, so a change to moamalat_hash that alters the canonical string, the
field names, the key decoding or the output case fails the test.
"""

import hmac
import unittest
from hashlib import sha256

from store_core.providers.payments import moamalat_hash as mh

# A throwaway test key (hex), of the shape Moamalat hands out.
KEY = "39ED9A1B5D1F4D1EA4A1F2B3C4D5E6F7"


def reference_hmac(canonical: str, key_hex: str = KEY) -> str:
	return hmac.new(bytes.fromhex(key_hex), canonical.encode("utf-8"), sha256).hexdigest().upper()


class TestCanonicalString(unittest.TestCase):
	def test_fields_are_sorted_alphabetically(self):
		self.assertEqual(
			mh.canonical_string({"TerminalId": "9", "Amount": 1, "MerchantId": "7"}),
			"Amount=1&MerchantId=7&TerminalId=9",
		)

	def test_empty_value_keeps_its_field(self):
		self.assertEqual(mh.canonical_string({"MerchantReference": None, "Amount": 5}), "Amount=5&MerchantReference=")

	def test_request_uses_the_documented_five_fields(self):
		self.assertEqual(
			tuple(sorted(mh.request_fields("M", "T", 1000, "L-1", "202609261830"))), mh.REQUEST_FIELDS
		)


class TestRequestHash(unittest.TestCase):
	def test_matches_the_documented_algorithm(self):
		canonical = "Amount=250500&DateTimeLocalTrxn=202609261830&MerchantId=1234567890123&MerchantReference=L-00042&TerminalId=98765432"
		self.assertEqual(
			mh.request_hash("1234567890123", "98765432", 250500, "L-00042", "202609261830", KEY),
			reference_hmac(canonical),
		)

	def test_output_is_uppercase_hex_of_64_chars(self):
		digest = mh.request_hash("M", "T", 1000, "L-1", "202609261830", KEY)
		self.assertEqual(len(digest), 64)
		self.assertEqual(digest, digest.upper())
		int(digest, 16)  # raises if it is not hex

	def test_lightbox_params_use_the_widget_field_names(self):
		params = mh.lightbox_params("M1", "T1", 250500, "L-00042", "202609261830", KEY)
		self.assertEqual(
			sorted(params), ["AmountTrxn", "MID", "MerchantReference", "SecureHash", "TID", "TrxDateTime"]
		)
		self.assertEqual(params["AmountTrxn"], 250500)
		# the widget params carry the hash built from the *hash* field names
		self.assertEqual(
			params["SecureHash"], mh.request_hash("M1", "T1", 250500, "L-00042", "202609261830", KEY)
		)

	def test_a_missing_or_invalid_key_is_rejected(self):
		for bad in ("", None, "not-hex", "ABC"):
			with self.subTest(key=bad):
				with self.assertRaises(mh.MoamalatConfigError):
					mh.request_hash("M", "T", 1, "L-1", "202609261830", bad)


class TestCallbackHash(unittest.TestCase):
	def payload(self) -> dict:
		return {
			"Amount": "250500",
			"Currency": "434",
			"MerchantReference": "L-00042",
			"NetworkReference": "987654321",
			"PaidThrough": "Card",
			"PayerAccount": "4111********1111",
			"PayerName": "SARA",
			"SystemReference": "123456",
			"TxnDate": "202609261830",
		}

	def test_hash_covers_every_field_except_securehash(self):
		payload = self.payload()
		expected = reference_hmac(mh.canonical_string(payload))
		payload["SecureHash"] = expected
		self.assertTrue(mh.callback_hash_matches(payload, KEY))

	def test_a_tampered_amount_is_rejected(self):
		payload = self.payload()
		payload["SecureHash"] = mh.callback_hash(payload, KEY)
		payload["Amount"] = "1000"  # customer tries to pay 1 LYD for a 250.5 LYD order
		self.assertFalse(mh.callback_hash_matches(payload, KEY))

	def test_an_added_field_is_rejected(self):
		payload = self.payload()
		payload["SecureHash"] = mh.callback_hash(payload, KEY)
		payload["Extra"] = "x"
		self.assertFalse(mh.callback_hash_matches(payload, KEY))

	def test_a_missing_hash_is_rejected(self):
		self.assertFalse(mh.callback_hash_matches(self.payload(), KEY))

	def test_lowercase_hash_from_the_gateway_still_matches(self):
		payload = self.payload()
		payload["SecureHash"] = mh.callback_hash(payload, KEY).lower()
		self.assertTrue(mh.callback_hash_matches(payload, KEY))

	def test_error_callback_fields(self):
		self.assertIn("ErrorMessage", mh.ERROR_FIELDS)
		self.assertEqual(tuple(sorted(mh.ERROR_FIELDS)), mh.ERROR_FIELDS)


class TestAmountUnits(unittest.TestCase):
	def test_lyd_converts_to_dirham(self):
		self.assertEqual(mh.to_minor_units(250.5), 250500)
		self.assertEqual(mh.to_minor_units(1), 1000)
		self.assertEqual(mh.to_minor_units(0.125), 125)

	def test_rounding_does_not_lose_a_dirham(self):
		# 285.53 * 1000 is 285529.99999... in binary floating point
		self.assertEqual(mh.to_minor_units(285.53), 285530)

	def test_round_trip(self):
		self.assertEqual(mh.from_minor_units(mh.to_minor_units(250.5)), 250.5)
