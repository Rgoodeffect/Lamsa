"""Install / migrate hooks and the explicit bootstrap command.

`after_install` and `after_migrate` only add store_core's own custom fields and roles.
They never change core ERPNext settings.

`bootstrap` creates the store's master data (service items, API user, default settings).
It is run explicitly by the site owner:

    bench --site <site> execute store_core.setup.install.bootstrap \
        --kwargs "{'company': 'Lamsa', 'warehouse': 'Stores - L', 'price_list': 'Standard Selling'}"
"""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from store_core.setup.custom_fields import CUSTOM_FIELDS

ROLES = (
	# name, desk_access
	("Lamsa Storefront API", 0),
	("Lamsa Store Manager", 1),
	("Lamsa Delivery Agent", 0),
)

#: Role Profile assigned to the person who runs the store.
#:
#: "Lamsa Store Manager" on its own only covers store_core's own DocTypes (settings, zones, agents,
#: assignments, settlements). The catalog lives in standard ERPNext DocTypes whose permissions belong
#: to standard roles, so managing products, prices and offers needs those too:
#:   Item / Item Group / Item Attribute -> Item Manager
#:   Item Price                         -> Sales Master Manager
#:   Pricing Rule                       -> Sales Manager
#:   Sales Order / Delivery Note        -> Sales User, Stock User
#:   Payment Entry, invoices            -> Accounts User
#: Bundling them in a Role Profile keeps store_core from adding Custom DocPerms to core DocTypes,
#: which would replace their standard permissions for everyone.
STORE_MANAGER_PROFILE = "Lamsa Store Manager"
STORE_MANAGER_ROLES = (
	"Lamsa Store Manager",
	"Item Manager",
	"Sales Master Manager",
	"Sales Manager",
	"Sales User",
	"Stock User",
	"Accounts User",
)

GIFT_WRAP_ITEM = "LAMSA-GIFT-WRAP"
DELIVERY_ITEM = "LAMSA-DELIVERY"
API_USER = "storefront-api@lamsa.local"


def after_install():
	apply_custom_fields()
	create_roles()
	create_store_manager_profile()


def after_migrate():
	apply_custom_fields()
	create_roles()
	create_store_manager_profile()


def before_uninstall():
	"""Remove only the custom fields store_core created (data in them is lost)."""
	for doctype, fields in CUSTOM_FIELDS.items():
		for field in fields:
			name = f"{doctype}-{field['fieldname']}"
			if frappe.db.exists("Custom Field", name):
				frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def apply_custom_fields():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


def create_roles():
	for role_name, desk_access in ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk_access}).insert(
				ignore_permissions=True
			)


def create_store_manager_profile():
	"""Create/refresh the Role Profile that gives one user everything running the store needs.

	Assign it on the User form (Role Profile field) instead of ticking roles by hand. Only roles that
	actually exist on the site are included, so it works whether or not every ERPNext module is set up.
	"""
	roles = [r for r in STORE_MANAGER_ROLES if frappe.db.exists("Role", r)]
	if not roles:
		return
	if frappe.db.exists("Role Profile", STORE_MANAGER_PROFILE):
		profile = frappe.get_doc("Role Profile", STORE_MANAGER_PROFILE)
	else:
		profile = frappe.new_doc("Role Profile")
		profile.role_profile = STORE_MANAGER_PROFILE
	existing = {row.role for row in profile.roles}
	for role in roles:
		if role not in existing:
			profile.append("roles", {"role": role})
	profile.flags.ignore_permissions = True
	profile.save()


@frappe.whitelist()
def bootstrap(
	company: str | None = None,
	warehouse: str | None = None,
	price_list: str | None = None,
	create_api_user: bool = True,
):
	"""Create service items, the storefront API user and default Lamsa Settings.

	Idempotent: existing records are left as they are. Prints the API key/secret once.
	"""
	frappe.only_for("System Manager")

	company = company or frappe.defaults.get_global_default("company")
	if not company:
		frappe.throw(_("Pass company=... or set a default company"))

	currency = frappe.db.get_value("Company", company, "default_currency")
	price_list = price_list or frappe.db.get_single_value("Selling Settings", "selling_price_list")
	warehouse = warehouse or frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 0, "disabled": 0}, "name", order_by="creation asc"
	)

	for code, name in ((GIFT_WRAP_ITEM, "تغليف هدية"), (DELIVERY_ITEM, "رسوم التوصيل")):
		if not frappe.db.exists("Item", code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": code,
					"item_name": name,
					"item_group": _services_group(),
					"stock_uom": "Nos",
					"is_stock_item": 0,
					"include_item_in_manufacturing": 0,
					"description": name,
				}
			).insert(ignore_permissions=True)

	if price_list and not frappe.db.exists(
		"Item Price", {"item_code": GIFT_WRAP_ITEM, "price_list": price_list}
	):
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": GIFT_WRAP_ITEM,
				"price_list": price_list,
				"price_list_rate": 10,
			}
		).insert(ignore_permissions=True)

	settings = frappe.get_single("Lamsa Settings")
	settings.company = settings.company or company
	settings.selling_price_list = settings.selling_price_list or price_list
	settings.warehouse = settings.warehouse or warehouse
	settings.currency = settings.currency or currency
	settings.customer_group = (
		settings.customer_group
		or frappe.db.get_single_value("Selling Settings", "customer_group")
		or _first("Customer Group", {"is_group": 0})
	)
	settings.territory = (
		settings.territory
		or frappe.db.get_single_value("Selling Settings", "territory")
		or _first("Territory", {"is_group": 0})
	)
	settings.gift_wrap_item = settings.gift_wrap_item or GIFT_WRAP_ITEM
	settings.delivery_fee_item = settings.delivery_fee_item or DELIVERY_ITEM
	settings.cod_cash_account = settings.cod_cash_account or frappe.db.get_value(
		"Company", company, "default_cash_account"
	)
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)

	result = {"settings": "Lamsa Settings updated"}
	if create_api_user:
		result.update(_create_api_user())

	frappe.db.commit()  # bench execute: persist before printing credentials
	print(frappe.as_json(result, indent=2))
	return result


def _services_group() -> str:
	for candidate in ("Services", _("Services")):
		if frappe.db.exists("Item Group", candidate):
			return candidate
	return _first("Item Group", {"is_group": 0}) or "All Item Groups"


def _first(doctype, filters):
	return frappe.db.get_value(doctype, filters, "name", order_by="creation asc")


def _create_api_user() -> dict:
	if frappe.db.exists("User", API_USER):
		return {"api_user": API_USER, "note": "User exists; regenerate keys from the User form if needed"}

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": API_USER,
			"first_name": "Lamsa Storefront",
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "Lamsa Storefront API"}],
		}
	)
	user.insert(ignore_permissions=True)
	api_secret = frappe.generate_hash(length=15)
	user.api_key = frappe.generate_hash(length=15)
	user.api_secret = api_secret
	user.save(ignore_permissions=True)
	return {
		"api_user": API_USER,
		"ERP_API_KEY": user.api_key,
		"ERP_API_SECRET": api_secret,
		"note": "Put these in storefront/.env.local now; the secret cannot be shown again.",
	}
