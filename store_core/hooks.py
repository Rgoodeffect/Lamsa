app_name = "store_core"
app_title = "Lamsa Store"
app_publisher = "Lamsa"
app_description = (
	"Lamsa (لمسة) store backend: storefront API, delivery management and integrations for ERPNext"
)
app_email = "rgoodeffect@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# Installation
# ------------
# Custom fields and roles are declared in code (store_core/setup/custom_fields.py) and applied
# idempotently on install and on every migrate. Service items, default settings and the API user
# are NOT created automatically: run `bench --site <site> execute store_core.setup.install.bootstrap`.
after_install = "store_core.setup.install.after_install"
after_migrate = "store_core.setup.install.after_migrate"
before_uninstall = "store_core.setup.install.before_uninstall"

# Document Events
# ---------------
doc_events = {
	"Item": {
		"before_validate": "store_core.services.catalog_hooks.item_before_validate",
		"on_update": "store_core.services.revalidate.on_catalog_change",
		"on_trash": "store_core.services.revalidate.on_catalog_change",
	},
	"Item Group": {
		"before_validate": "store_core.services.catalog_hooks.item_group_before_validate",
		"on_update": "store_core.services.revalidate.on_catalog_change",
	},
	"Item Price": {
		"on_update": "store_core.services.revalidate.on_catalog_change",
		"on_trash": "store_core.services.revalidate.on_catalog_change",
	},
	"Bin": {
		"on_update": "store_core.services.revalidate.on_stock_change",
	},
	"Customer": {
		"validate": "store_core.services.customer.customer_validate",
	},
}

# Provider registries
# -------------------
# Other apps can register providers by adding entries to these hooks in their own hooks.py.
# Each entry is "code:dotted.path.to.Class". See README "Adding a payment provider".
lamsa_payment_providers = [
	"cod:store_core.providers.payments.cod.CashOnDelivery",
	"moamalat:store_core.providers.payments.moamalat.MoamalatProvider",
	"sadad:store_core.providers.payments.sadad.SadadProvider",
]
lamsa_shipping_providers = [
	"manual:store_core.providers.shipping.manual.ManualShipping",
]
lamsa_notification_channels = [
	"log:store_core.providers.notifications.log.LogChannel",
	"whatsapp:store_core.providers.notifications.whatsapp.WhatsAppChannel",
]

export_python_type_annotations = True

# Translation
# -----------
# Arabic strings for desk labels live in store_core/locale/ar.po
