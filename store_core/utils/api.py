"""Helpers shared by store_core.api.v1 endpoints.

Every storefront endpoint:
- is only callable by the storefront server's API user (role "Lamsa Storefront API") or a
  System Manager; guests are rejected, so ERPNext is never directly reachable from browsers;
- returns {"ok": true, "data": ...} or {"ok": false, "error": {"code", "details"}} with a 4xx
  status, so the storefront can show a translated Arabic message per error code;
- can be rate limited per end-customer IP. The storefront forwards the shopper's IP in
  X-Lamsa-Client-IP; it is trusted only because the caller is the authenticated API user.
"""

import json
from functools import wraps

import frappe

from store_core.services.orders import CheckoutError

ALLOWED_ROLES = ("Lamsa Storefront API", "System Manager")
CLIENT_IP_HEADER = "X-Lamsa-Client-IP"


def storefront_endpoint(rate_limit: tuple[int, int] | None = None):
	"""rate_limit=(limit, seconds) per client IP and endpoint."""

	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			frappe.only_for(ALLOWED_ROLES)
			if rate_limit:
				_check_rate_limit(fn.__name__, *rate_limit)
			try:
				return {"ok": True, "data": fn(*args, **kwargs)}
			except CheckoutError as e:
				frappe.db.rollback()
				frappe.local.response.http_status_code = 404 if e.code == "order_not_found" else 422
				return {"ok": False, "error": {"code": e.code, "details": e.details}}

		return wrapper

	return decorator


def client_ip() -> str:
	forwarded = frappe.get_request_header(CLIENT_IP_HEADER) if frappe.request else None
	return (forwarded or getattr(frappe.local, "request_ip", None) or "unknown").strip()[:64]


def _check_rate_limit(endpoint: str, limit: int, seconds: int):
	if not frappe.request:
		return
	key = frappe.cache.make_key(f"lamsa:rl:{endpoint}:{client_ip()}")
	count = frappe.cache.incrby(key, 1)
	if count == 1:
		frappe.cache.expire(key, seconds)
	if count > limit:
		frappe.local.response.http_status_code = 429
		raise frappe.TooManyRequestsError


def parse_json(value, default=None):
	if value is None or value == "":
		return default
	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			raise CheckoutError("invalid_request")
	return value


def parse_list(value) -> list[str]:
	"""Accept a list, a JSON list or a comma-separated string."""
	if value is None or value == "":
		return []
	if isinstance(value, str):
		value = value.strip()
		if value.startswith("["):
			value = parse_json(value, [])
		else:
			value = value.split(",")
	return [str(v).strip() for v in value if str(v).strip()][:50]
