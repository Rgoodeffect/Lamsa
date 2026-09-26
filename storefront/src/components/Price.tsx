import { formatPrice, formatPriceRange } from "@/lib/format";
import { t } from "@/lib/i18n";

/**
 * A price, with the price-list price struck through beside it when the item is discounted.
 *
 * `listMin`/`listMax` are the price-list prices; when they are higher than what the customer pays,
 * the difference comes from a Pricing Rule in ERPNext. The cart recalculates everything, so this is
 * a display of the catalog price, never an input to the total.
 */
export function Price({
  min,
  max,
  listMin,
  listMax,
  currency,
  className = "",
}: {
  min: number;
  max?: number;
  listMin?: number;
  listMax?: number;
  currency: string;
  className?: string;
}) {
  const now = max === undefined ? formatPrice(min, currency) : formatPriceRange(min, max, currency);
  const listLow = listMin ?? min;
  const listHigh = max === undefined ? listLow : (listMax ?? max);
  const onSale = listLow > min || listHigh > (max ?? min);
  const was = max === undefined ? formatPrice(listLow, currency) : formatPriceRange(listLow, listHigh, currency);
  const off = onSale && listHigh > 0 ? Math.round((1 - (max ?? min) / listHigh) * 100) : 0;

  if (!onSale) {
    return <span className={`font-semibold text-primary-700 ${className}`}>{now}</span>;
  }
  return (
    <span className={`flex flex-wrap items-baseline gap-2 ${className}`}>
      <span className="font-semibold text-danger">{now}</span>
      <s className="text-sm font-normal text-muted" aria-label={t("price.was")}>
        {was}
      </s>
      {off > 0 ? (
        <span className="rounded-pill bg-danger/10 px-2 py-0.5 text-xs font-semibold text-danger">
          {t("price.off").replace("{percent}", String(off))}
        </span>
      ) : null}
    </span>
  );
}
