"""Catalog display discounts from ERPNext Pricing Rules.

The cart and checkout use ERPNext's own pricing engine, which is authoritative. Running that engine
once per item would be far too slow for a catalog index, so the price shown on category and product
pages is computed here from the Pricing Rules directly.

To keep the two from disagreeing, this is deliberately conservative: it only considers rules that
apply to a single item at qty 1 regardless of who is shopping, i.e. rules that a guest checkout is
certain to receive. Anything conditional — a coupon, a quantity break, a rule aimed at another
customer group, a cumulative or mixed-condition rule, a "free item" rule — is ignored and the item
simply shows its price-list price. So the catalog may under-advertise a discount, but it never
promises one the cart will not honour.

Only the single best-priority rule per item is applied; ERPNext can combine several, which is
another reason the cart total is the one that counts.
"""

import frappe
from frappe.utils import cint, flt, getdate, nowdate

#: Rules are matched most specific first, and ERPNext's own `priority` wins over that.
APPLY_ON_SPECIFICITY = {"Item Code": 0, "Item Group": 1, "Brand": 2}
CHILD_TABLES = {
	"Item Code": ("Pricing Rule Item Code", "item_code"),
	"Item Group": ("Pricing Rule Item Group", "item_group"),
	"Brand": ("Pricing Rule Brand", "brand"),
}


def catalog_discounts(settings, groups: dict) -> list[dict]:
	"""The catalog-safe selling rules, best first. Empty when Pricing Rules cannot be read."""
	try:
		return _load_rules(settings, groups)
	except Exception:
		# A pricing rule must never take the storefront down: fall back to price-list prices.
		frappe.log_error(title="Lamsa: could not read Pricing Rules for the catalog")
		return []


def _load_rules(settings, groups: dict) -> list[dict]:
	today = getdate(nowdate())
	rows = frappe.get_all(
		"Pricing Rule",
		filters={
			"disable": 0,
			"selling": 1,
			"price_or_product_discount": "Price",
			"coupon_code_based": 0,
			"mixed_conditions": 0,
			"is_cumulative": 0,
			"apply_on": ["in", list(APPLY_ON_SPECIFICITY)],
		},
		fields=[
			"name",
			"apply_on",
			"rate_or_discount",
			"rate",
			"discount_percentage",
			"discount_amount",
			"min_qty",
			"max_qty",
			"valid_from",
			"valid_upto",
			"priority",
			"applicable_for",
			"customer_group",
			"territory",
			"currency",
			"for_price_list",
			"company",
		],
	)

	rules = []
	for row in rows:
		if not _applies_now(row, today) or not _applies_to_a_single_unit(row) or not _applies_to_guests(row, settings):
			continue
		targets = _targets(row)
		if not targets:
			continue
		rules.append(
			{
				"name": row.name,
				"apply_on": row.apply_on,
				"rate_or_discount": row.rate_or_discount,
				"rate": flt(row.rate),
				"discount_percentage": flt(row.discount_percentage),
				"discount_amount": flt(row.discount_amount),
				"priority": cint(row.priority),
				"targets": _expand_groups(targets, groups) if row.apply_on == "Item Group" else targets,
			}
		)

	# Highest priority first, then the most specific kind of rule.
	rules.sort(key=lambda r: (-r["priority"], APPLY_ON_SPECIFICITY[r["apply_on"]]))
	return rules


def _applies_now(row, today) -> bool:
	if row.valid_from and getdate(row.valid_from) > today:
		return False
	if row.valid_upto and getdate(row.valid_upto) < today:
		return False
	return True


def _applies_to_a_single_unit(row) -> bool:
	"""A quantity break is not something a catalog page can promise."""
	if flt(row.min_qty) > 1:
		return False
	return not (flt(row.max_qty) and flt(row.max_qty) < 1)


def _applies_to_guests(row, settings) -> bool:
	"""Only rules every storefront shopper gets: the store's own group/territory, or no condition."""
	if row.company and row.company != settings.company:
		return False
	if row.currency and row.currency != settings.currency:
		return False
	if row.for_price_list and row.for_price_list != settings.selling_price_list:
		return False
	if not row.applicable_for:
		return True
	if row.applicable_for == "Customer Group":
		return bool(settings.customer_group) and row.customer_group == settings.customer_group
	if row.applicable_for == "Territory":
		return bool(settings.territory) and row.territory == settings.territory
	return False  # Customer, Campaign, Sales Partner: not every shopper


def _targets(row) -> set[str]:
	doctype, fieldname = CHILD_TABLES[row.apply_on]
	return {
		v[fieldname]
		for v in frappe.get_all(
			doctype, filters={"parent": row.name, "parenttype": "Pricing Rule"}, fields=[fieldname]
		)
		if v.get(fieldname)
	}


def _expand_groups(targets: set[str], groups: dict) -> set[str]:
	"""A rule on a parent Item Group covers every group below it, as ERPNext does."""
	expanded = set(targets)
	for name in targets:
		root = groups.get(name)
		if not root:
			continue
		expanded.update(
			g["name"] for g in groups.values() if g["lft"] >= root["lft"] and g["rgt"] <= root["rgt"]
		)
	return expanded


def match(rules: list[dict], item_code: str, item_group: str | None, brand: str | None) -> dict | None:
	"""The best catalog-safe rule for one item, or None."""
	for rule in rules:
		key = {"Item Code": item_code, "Item Group": item_group, "Brand": brand}[rule["apply_on"]]
		if key and key in rule["targets"]:
			return rule
	return None


def discounted(list_rate: float, rule: dict | None) -> float:
	"""Price after the rule. Never below zero, and never above the price-list rate."""
	list_rate = flt(list_rate)
	if not rule:
		return list_rate
	kind = rule["rate_or_discount"]
	if kind == "Discount Percentage":
		rate = list_rate * (1 - flt(rule["discount_percentage"]) / 100)
	elif kind == "Discount Amount":
		rate = list_rate - flt(rule["discount_amount"])
	elif kind == "Rate":
		rate = flt(rule["rate"])
	else:
		return list_rate
	return min(list_rate, max(flt(rate, 2), 0.0))
