"""Libyan mobile number validation and normalization.

Pure Python (no frappe import) so it can be unit tested without a bench.
The storefront mirrors these rules in `storefront/src/lib/phone.ts`; both are tested
against `store_core/tests/unit/phone_cases.json`.

Accepted inputs (spaces, dashes, dots and parentheses are ignored, Arabic-Indic and
Persian digits are converted):
    0912345678, 912345678, +218912345678, 00218912345678, 218912345678
Canonical output: +2189XXXXXXXX (E.164).
"""

import re

COUNTRY_CODE = "218"
# 91/93 Al Madar, 92/94 Libyana, 95 LTT (Libya Telecom & Technology) mobile ranges.
MOBILE_PREFIXES = ("91", "92", "93", "94", "95")

_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_STRIP = re.compile(r"[\s\-\.\(\)‎‏‪-‮]")


class InvalidPhone(ValueError):
	pass


def normalize_libyan_phone(raw: str | None) -> str:
	"""Return the phone as +2189XXXXXXXX or raise InvalidPhone."""
	if not raw:
		raise InvalidPhone("empty")

	value = _STRIP.sub("", str(raw).translate(_DIGIT_MAP))

	if value.startswith("+"):
		value = value[1:]
		if not value.startswith(COUNTRY_CODE):
			raise InvalidPhone("not a Libyan number")
	elif value.startswith("00"):
		value = value[2:]
		if not value.startswith(COUNTRY_CODE):
			raise InvalidPhone("not a Libyan number")

	if not value.isdigit():
		raise InvalidPhone("contains invalid characters")

	if value.startswith(COUNTRY_CODE) and len(value) == 12:
		national = value[3:]
	elif value.startswith("0") and len(value) == 10:
		national = value[1:]
	elif len(value) == 9:
		national = value
	else:
		raise InvalidPhone("wrong length")

	if national[:2] not in MOBILE_PREFIXES:
		raise InvalidPhone("not a Libyan mobile prefix")

	return f"+{COUNTRY_CODE}{national}"


def is_valid_libyan_phone(raw: str | None) -> bool:
	try:
		normalize_libyan_phone(raw)
		return True
	except InvalidPhone:
		return False


def local_format(e164: str) -> str:
	"""+218912345678 -> 091 234 5678 (for display and delivery notes)."""
	national = "0" + e164[-9:]
	return f"{national[:3]} {national[3:6]} {national[6:]}"


def whatsapp_number(e164: str) -> str:
	"""+218912345678 -> 218912345678 (wa.me format)."""
	return e164.lstrip("+")
