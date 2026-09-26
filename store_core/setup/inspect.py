"""Read-only pre-install check for a production site.

Usage (before or after `bench install-app store_core`):

    bench --site <site> execute store_core.setup.inspect.report

It only reads data. Nothing is created or changed.
"""

import frappe


def report():
	lines: list[str] = []
	problems: list[str] = []

	def ok(msg):
		lines.append(f"  [ok]   {msg}")

	def warn(msg):
		lines.append(f"  [warn] {msg}")
		problems.append(msg)

	lines.append("== Apps ==")
	apps = frappe.get_installed_apps()
	for app in apps:
		try:
			version = frappe.get_attr(f"{app}.__version__")
		except Exception:
			version = "?"
		lines.append(f"  {app} {version}")
	if not frappe.__version__.startswith("16."):
		warn(f"Frappe {frappe.__version__} detected; store_core targets v16")
	if "erpnext" not in apps:
		warn("ERPNext is not installed on this site")
	if "webshop" in apps:
		warn(
			"webshop app is installed; store_core does not depend on it, but check for URL clashes (/shop, /cart)"
		)

	lines.append("== Companies ==")
	companies = frappe.get_all(
		"Company", fields=["name", "default_currency", "default_cash_account", "country"]
	)
	for c in companies:
		lines.append(
			f"  {c.name}: currency={c.default_currency} cash={c.default_cash_account} country={c.country}"
		)
	if not any(c.default_currency == "LYD" for c in companies):
		warn("No company uses LYD as default currency")

	lines.append("== Selling price lists ==")
	for pl in frappe.get_all("Price List", filters={"selling": 1, "enabled": 1}, fields=["name", "currency"]):
		lines.append(f"  {pl.name} ({pl.currency})")

	lines.append("== Warehouses (leaf) ==")
	for w in frappe.get_all(
		"Warehouse", filters={"is_group": 0, "disabled": 0}, fields=["name", "company"], limit=30
	):
		lines.append(f"  {w.name} [{w.company}]")

	lines.append("== Items ==")
	lines.append(f"  items: {frappe.db.count('Item', {'disabled': 0})}")
	lines.append(f"  templates (has_variants): {frappe.db.count('Item', {'has_variants': 1})}")
	lines.append(f"  variants: {frappe.db.count('Item', {'variant_of': ['is', 'set']})}")
	attrs = frappe.get_all("Item Attribute", pluck="name")
	lines.append(f"  attributes: {', '.join(attrs) or '-'}")
	if not any(a.lower() in ("size", "المقاس", "مقاس") for a in attrs):
		warn("No 'Size' Item Attribute found (needed for clothing variants)")
	if not any(a.lower() in ("color", "colour", "اللون", "لون") for a in attrs):
		warn("No 'Color' Item Attribute found (needed for clothing variants)")

	lines.append("== Item groups ==")
	for g in frappe.get_all("Item Group", fields=["name", "parent_item_group", "is_group"], order_by="lft"):
		lines.append(f"  {g.name} (parent={g.parent_item_group}{', group' if g.is_group else ''})")

	lines.append("== Selling Settings ==")
	ss = frappe.get_single("Selling Settings")
	for f in (
		"cust_master_name",
		"customer_group",
		"territory",
		"selling_price_list",
		"so_required",
		"dn_required",
	):
		lines.append(f"  {f}: {ss.get(f)}")

	lines.append("== Stock Settings ==")
	st = frappe.get_single("Stock Settings")
	for f in ("default_warehouse", "allow_negative_stock", "enable_stock_reservation"):
		lines.append(f"  {f}: {st.get(f)}")

	lines.append("== Site ==")
	lines.append(f"  developer_mode: {frappe.conf.get('developer_mode')}")
	lines.append(f"  host_name: {frappe.conf.get('host_name')}")
	lines.append(
		f"  scheduler: {'enabled' if not frappe.utils.scheduler.is_scheduler_disabled() else 'DISABLED'}"
	)
	if frappe.conf.get("developer_mode"):
		warn("developer_mode is on; turn it off on production")

	if "store_core" in apps:
		lines.append("== store_core ==")
		settings = frappe.get_single("Lamsa Settings")
		for f in (
			"company",
			"selling_price_list",
			"warehouse",
			"gift_wrap_item",
			"delivery_fee_item",
			"cod_cash_account",
		):
			value = settings.get(f)
			(ok if value else warn)(f"Lamsa Settings.{f} = {value}")
		zones = frappe.db.count("Delivery Zone", {"enabled": 1})
		(ok if zones else warn)(f"enabled delivery zones: {zones}")

	lines.append("")
	lines.append(f"== {len(problems)} warning(s) ==")
	print("\n".join(lines))
	return {"warnings": problems}
