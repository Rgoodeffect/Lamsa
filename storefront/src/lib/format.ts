import { t } from "./i18n";

// "1,250.5" grouping (ar-LY would give "1.250,5", which reads oddly on price tags)
const number = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

/** 250 -> "250 LYD" in Arabic (Western digits are the norm on Libyan price tags). */
export function formatPrice(value: number | null | undefined, currency = "LYD"): string {
  const amount = number.format(Number(value ?? 0));
  const symbol = currency === "LYD" ? t("common.currency") : currency;
  return `${amount} ${symbol}`;
}

export function formatPriceRange(min: number, max: number, currency = "LYD"): string {
  if (Math.abs(max - min) < 0.005) return formatPrice(min, currency);
  return `${t("product.from")} ${formatPrice(min, currency)}`;
}

export function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value.replace(" ", "T")) : value;
  return new Intl.DateTimeFormat("ar-LY-u-nu-latn", { dateStyle: "medium" }).format(date);
}
