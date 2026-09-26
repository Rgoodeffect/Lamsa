import type { Quote } from "@/lib/erp/types";
import { formatPrice } from "@/lib/format";
import { t } from "@/lib/i18n";

export function Summary({ quote, showDelivery, loading }: { quote: Quote | null; showDelivery: boolean; loading: boolean }) {
  const discountLabel = quote?.coupon ? t("checkout.coupon_discount") : t("checkout.discount");
  const row = (label: string, value: string, testId?: string) => (
    <div className="flex justify-between py-1.5">
      <dt className="text-muted">{label}</dt>
      <dd data-testid={testId}>{value}</dd>
    </div>
  );
  if (!quote) return <p className="text-sm text-muted">{t("cart.prices_updating")}</p>;
  return (
    <dl className={`text-sm transition ${loading ? "opacity-60" : ""}`} aria-busy={loading}>
      {row(t("checkout.subtotal"), formatPrice(quote.subtotal, quote.currency), "summary-subtotal")}
      {quote.discount > 0 && row(discountLabel, `- ${formatPrice(quote.discount, quote.currency)}`, "summary-discount")}
      {quote.gift_wrap_fee > 0 && row(t("checkout.gift_wrap_fee"), formatPrice(quote.gift_wrap_fee, quote.currency))}
      {showDelivery &&
        row(
          t("checkout.delivery_fee"),
          quote.zone ? (quote.delivery_fee > 0 ? formatPrice(quote.delivery_fee, quote.currency) : t("common.free")) : t("checkout.delivery_fee_pending"),
          "summary-delivery",
        )}
      <div className="mt-2 flex justify-between border-t border-line pt-3 text-base font-bold">
        <dt>{t("checkout.total")}</dt>
        <dd data-testid="summary-total">{formatPrice(quote.grand_total, quote.currency)}</dd>
      </div>
    </dl>
  );
}
