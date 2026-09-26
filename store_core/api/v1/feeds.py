"""Marketing feeds: /api/method/store_core.api.v1.feeds.meta_catalog"""

import frappe

from store_core.services import catalog
from store_core.services.feed import feed_rows
from store_core.utils.api import storefront_endpoint


@frappe.whitelist(methods=["GET"])
@storefront_endpoint()
def meta_catalog():
	index = catalog.get_index()
	return {"currency": index["currency"], "items": feed_rows(index)}
