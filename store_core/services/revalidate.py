"""Tell the Next.js storefront to refresh ISR pages when catalog data changes.

The storefront exposes POST /api/revalidate, protected by a shared secret
(LAMSA_REVALIDATE_SECRET here, REVALIDATE_SECRET in storefront/.env). Calls are debounced through a
deduplicated background job so a stock import does not fire thousands of requests.
"""

import frappe
import requests

from store_core.services import catalog
from store_core.services.settings import get_secret

JOB_ID = "lamsa-revalidate"


def on_catalog_change(doc, method=None):
	catalog.invalidate_index()
	request_revalidation(["catalog"])


def on_stock_change(doc, method=None):
	if not doc.has_value_changed("actual_qty") and not doc.has_value_changed("reserved_qty"):
		return
	warehouse = frappe.get_cached_doc("Lamsa Settings").warehouse
	if warehouse and doc.warehouse != warehouse:
		return
	catalog.invalidate_index()
	request_revalidation(["products"])


def request_revalidation(tags: list[str]):
	if not _configured() or frappe.flags.in_test or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	frappe.enqueue(
		"store_core.services.revalidate.send",
		queue="short",
		job_id=JOB_ID,
		deduplicate=True,
		enqueue_after_commit=True,
		tags=tags,
	)


def _configured() -> bool:
	return bool(get_secret("lamsa_revalidate_url") and get_secret("lamsa_revalidate_secret"))


def send(tags: list[str] | None = None):
	url, secret = get_secret("lamsa_revalidate_url"), get_secret("lamsa_revalidate_secret")
	if not (url and secret):
		return
	try:
		response = requests.post(
			url,
			json={"tags": tags or ["catalog"]},
			headers={"Authorization": f"Bearer {secret}"},
			timeout=10,
		)
		response.raise_for_status()
	except Exception:
		frappe.log_error(title="Lamsa storefront revalidation failed")
