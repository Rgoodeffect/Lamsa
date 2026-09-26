"""Moamalat SecureHash (pure Python, unit tested without a bench).

https://docs.moamalat.net/lightBox.html — the algorithm for all three directions (request,
complete callback, error callback) is the same:

1. take the applicable fields and sort them alphabetically by field name,
2. join them as "field1=value1&field2=value2...",
3. HMAC-SHA256 that string with the merchant secret key, hex-decoded,
4. render the digest as uppercase hex.

The field names used for the hash are NOT the Lightbox parameter names: the widget takes
MID/TID/AmountTrxn/TrxDateTime while the hash uses MerchantId/TerminalId/Amount/DateTimeLocalTrxn.
Getting that wrong is the usual cause of a rejected request, so the two namings are kept apart
here: `request_fields` builds the hash input, `lightbox_params` builds the widget input.
"""

import hmac
from hashlib import sha256

#: Fields hashed in a payment request.
REQUEST_FIELDS = ("Amount", "DateTimeLocalTrxn", "MerchantId", "MerchantReference", "TerminalId")
#: Fields hashed in an error callback.
ERROR_FIELDS = (
	"Amount",
	"DateTimeLocalTrxn",
	"ErrorMessage",
	"MerchantId",
	"MerchantReference",
	"TerminalId",
)
#: LYD has 3 decimals: the gateway wants the amount in dirham (1 LYD = 1000).
AMOUNT_MULTIPLIER = 1000


class MoamalatConfigError(ValueError):
	"""The merchant secret key is missing or not valid hex."""


def secure_hash(fields: dict, secret_key_hex: str) -> str:
	"""Uppercase hex HMAC-SHA256 of the sorted "k=v&k=v" string, keyed with the hex-decoded secret."""
	try:
		key = bytes.fromhex((secret_key_hex or "").strip())
	except ValueError:
		raise MoamalatConfigError("MOAMALAT_SECRET_KEY must be a hex string")
	if not key:
		raise MoamalatConfigError("MOAMALAT_SECRET_KEY is not set")
	return hmac.new(key, canonical_string(fields).encode("utf-8"), sha256).hexdigest().upper()


def canonical_string(fields: dict) -> str:
	"""Alphabetically sorted "field=value&field=value". Empty values keep their "field=" part."""
	return "&".join(f"{name}={_text(fields[name])}" for name in sorted(fields))


def _text(value) -> str:
	if value is None or value is False:
		return ""
	if value is True:
		return "true"
	return str(value)


def request_fields(merchant_id: str, terminal_id: str, amount_minor: int, reference: str, trx_datetime: str) -> dict:
	"""The five fields hashed in a payment request, under their hash names."""
	return {
		"Amount": amount_minor,
		"DateTimeLocalTrxn": trx_datetime,
		"MerchantId": merchant_id,
		"MerchantReference": reference,
		"TerminalId": terminal_id,
	}


def request_hash(
	merchant_id: str, terminal_id: str, amount_minor: int, reference: str, trx_datetime: str, secret_key_hex: str
) -> str:
	return secure_hash(
		request_fields(merchant_id, terminal_id, amount_minor, reference, trx_datetime), secret_key_hex
	)


def lightbox_params(
	merchant_id: str, terminal_id: str, amount_minor: int, reference: str, trx_datetime: str, secret_key_hex: str
) -> dict:
	"""The parameters the Lightbox widget itself takes, with the matching SecureHash."""
	return {
		"MID": merchant_id,
		"TID": terminal_id,
		"AmountTrxn": amount_minor,
		"MerchantReference": reference,
		"TrxDateTime": trx_datetime,
		"SecureHash": request_hash(
			merchant_id, terminal_id, amount_minor, reference, trx_datetime, secret_key_hex
		),
	}


def callback_hash(payload: dict, secret_key_hex: str) -> str:
	"""Hash of a gateway callback: every field it sent except SecureHash itself."""
	fields = {k: v for k, v in payload.items() if k != "SecureHash"}
	return secure_hash(fields, secret_key_hex)


def callback_hash_matches(payload: dict, secret_key_hex: str) -> bool:
	given = str(payload.get("SecureHash") or "")
	expected = callback_hash(payload, secret_key_hex)
	return hmac.compare_digest(given.upper(), expected)


def to_minor_units(amount: float) -> int:
	"""250.5 LYD -> 250500 dirham. Rounded, because the gateway takes an integer."""
	return int(round(float(amount) * AMOUNT_MULTIPLIER))


def from_minor_units(amount_minor) -> float:
	return int(amount_minor) / AMOUNT_MULTIPLIER
