# Copyright (c) 2026, Lamsa and contributors
# For license information, please see license.txt

"""One image vector, produced by one embedder, for one product image.

Rows are written by `store_core.services.image_search` in a background job and are never edited by
hand: the store manager can read or delete them, which is why there is no write permission for that
role. Deleting a row only costs a re-embed of that image.
"""

import frappe
from frappe.model.document import Document


class LamsaImageEmbedding(Document):
	def on_update(self):
		_invalidate()

	def on_trash(self):
		_invalidate()


def _invalidate():
	from store_core.services import image_search

	image_search.invalidate_index()
