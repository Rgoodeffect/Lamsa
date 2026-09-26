"""Custom fields added by store_core to standard ERPNext DocTypes.

Every field is prefixed with `lamsa_` and grouped in a "Lamsa" tab at the end of the form, so the
standard layout stays untouched. Applied idempotently by `setup.install.apply_custom_fields`
on install and on every `bench migrate`.
"""


def _tab(label="Lamsa"):
	return {"fieldname": "lamsa_tab", "fieldtype": "Tab Break", "label": label}


def _chain(fields: list[dict]) -> list[dict]:
	"""Set insert_after so fields keep the declared order inside the Lamsa tab."""
	previous = None
	out = []
	for field in fields:
		field = dict(field)
		if previous:
			field.setdefault("insert_after", previous)
		previous = field["fieldname"]
		out.append(field)
	return out


ORDER_FIELDS = [
	{
		"fieldname": "lamsa_order_no",
		"fieldtype": "Data",
		"label": "Store Order No",
		"read_only": 1,
		"in_standard_filter": 1,
		"search_index": 1,
		"no_copy": 0,
		"allow_on_submit": 0,
	},
	{"fieldname": "lamsa_gift_wrap", "fieldtype": "Check", "label": "Gift Wrap", "read_only": 1},
	{"fieldname": "lamsa_gift_message", "fieldtype": "Small Text", "label": "Gift Message", "read_only": 1},
]

CUSTOM_FIELDS: dict[str, list[dict]] = {
	"Item": _chain(
		[
			_tab(),
			{
				"fieldname": "lamsa_publish",
				"fieldtype": "Check",
				"label": "Publish in Store",
				"description": "Show this item (template) in the online store",
				"in_list_view": 0,
				"in_standard_filter": 1,
			},
			{"fieldname": "lamsa_featured", "fieldtype": "Check", "label": "Featured on Home Page"},
			{
				"fieldname": "lamsa_slug",
				"fieldtype": "Data",
				"label": "URL Slug",
				"unique": 0,
				"search_index": 1,
				"description": "Generated from the item name when empty",
			},
			{"fieldname": "lamsa_col1", "fieldtype": "Column Break"},
			{
				"fieldname": "lamsa_gender",
				"fieldtype": "Select",
				"label": "Gender",
				"options": "\nfemale\nmale\nunisex",
			},
			{
				"fieldname": "lamsa_age_range",
				"fieldtype": "Link",
				"label": "Age Range",
				"options": "Age Range",
				"description": "For kids' clothing filters",
			},
			{"fieldname": "lamsa_sec1", "fieldtype": "Section Break", "label": "Store Content"},
			{
				"fieldname": "lamsa_description_ar",
				"fieldtype": "Text Editor",
				"label": "Store Description (Arabic)",
			},
			{"fieldname": "lamsa_seo_title", "fieldtype": "Data", "label": "SEO Title"},
			{"fieldname": "lamsa_seo_description", "fieldtype": "Small Text", "label": "SEO Description"},
		]
	),
	"Item Group": _chain(
		[
			_tab(),
			{"fieldname": "lamsa_show_in_store", "fieldtype": "Check", "label": "Show in Store"},
			{"fieldname": "lamsa_slug", "fieldtype": "Data", "label": "URL Slug", "search_index": 1},
			{"fieldname": "lamsa_title_ar", "fieldtype": "Data", "label": "Arabic Title"},
			{"fieldname": "lamsa_sort", "fieldtype": "Int", "label": "Sort Order"},
			{"fieldname": "lamsa_col1", "fieldtype": "Column Break"},
			{
				"fieldname": "lamsa_size_guide",
				"fieldtype": "Link",
				"label": "Size Guide",
				"options": "Size Guide",
			},
			{"fieldname": "lamsa_has_age_filter", "fieldtype": "Check", "label": "Enable Age Range Filter"},
			{"fieldname": "lamsa_description_ar", "fieldtype": "Small Text", "label": "Arabic Description"},
		]
	),
	"Customer": _chain(
		[
			_tab(),
			{
				"fieldname": "lamsa_phone",
				"fieldtype": "Data",
				"label": "Store Phone (E.164)",
				"read_only": 1,
				"search_index": 1,
				"unique": 0,
				"in_standard_filter": 1,
				"description": "Normalized Libyan mobile used to match storefront orders",
			},
		]
	),
	"Sales Order": _chain(
		[
			_tab(),
			*ORDER_FIELDS,
			{"fieldname": "lamsa_col1", "fieldtype": "Column Break"},
			{
				"fieldname": "lamsa_source",
				"fieldtype": "Select",
				"label": "Order Source",
				"options": "\nStorefront\nWhatsApp\nPhone\nSocial",
				"read_only": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "lamsa_status",
				"fieldtype": "Data",
				"label": "Store Status",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"allow_on_submit": 1,
			},
			{
				"fieldname": "lamsa_payment_provider",
				"fieldtype": "Data",
				"label": "Payment Provider",
				"read_only": 1,
			},
			{
				"fieldname": "lamsa_payment_status",
				"fieldtype": "Select",
				"label": "Payment Status",
				"options": "\nUnpaid\nPaid\nFailed",
				"read_only": 1,
				"allow_on_submit": 1,
				"in_standard_filter": 1,
				"description": "Set by the gateway callback for online payments; cash orders stay Unpaid until settled",
			},
			{
				"fieldname": "lamsa_payment_reference",
				"fieldtype": "Data",
				"label": "Payment Reference",
				"read_only": 1,
				"allow_on_submit": 1,
				"search_index": 1,
				"description": "Gateway transaction reference; also makes the callback idempotent",
			},
			{"fieldname": "lamsa_sec1", "fieldtype": "Section Break", "label": "Delivery"},
			{
				"fieldname": "lamsa_delivery_zone",
				"fieldtype": "Link",
				"label": "Delivery Zone",
				"options": "Delivery Zone",
				"read_only": 1,
			},
			{
				"fieldname": "lamsa_phone",
				"fieldtype": "Data",
				"label": "Customer Phone",
				"read_only": 1,
				"search_index": 1,
			},
			{"fieldname": "lamsa_col2", "fieldtype": "Column Break"},
			{
				"fieldname": "lamsa_address_notes",
				"fieldtype": "Small Text",
				"label": "Address Notes",
				"read_only": 1,
			},
			{
				"fieldname": "lamsa_event_id",
				"fieldtype": "Data",
				"label": "Tracking Event ID",
				"read_only": 1,
				"search_index": 1,
				"hidden": 1,
			},
		]
	),
	"Item Attribute Value": [
		{
			"fieldname": "lamsa_swatch",
			"fieldtype": "Color",
			"label": "Store Swatch",
			"insert_after": "abbr",
			"in_list_view": 1,
			"columns": 1,
			"description": "Colour dot shown on the storefront (leave the Abbreviation as a short code: it becomes part of variant item codes)",
		},
	],
	"Coupon Code": [
		{
			"fieldname": "lamsa_discount_percent",
			"fieldtype": "Percent",
			"label": "Store Discount %",
			"insert_after": "description",
			"read_only": 1,
			"description": "Set when Lamsa rewards the coupon; kept here so changing the setting later does not re-price a coupon a customer already holds",
		},
	],
	"Delivery Note": _chain([_tab(), *ORDER_FIELDS]),
	"Sales Invoice": _chain([_tab(), *ORDER_FIELDS]),
}
