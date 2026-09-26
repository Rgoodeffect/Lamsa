"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { useCart } from "@/lib/cart-store";
import { formatPrice } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useQuote } from "@/lib/use-quote";

import { BagIcon } from "../Icons";
import { ProductImage } from "../ProductImage";
import { Summary } from "./Summary";

const noop = () => () => {};

export function CartView() {
  const hydrated = useSyncExternalStore(noop, () => true, () => false);
  const { quote, error, loading, lines } = useQuote();
  const setQty = useCart((s) => s.setQty);
  const remove = useCart((s) => s.remove);

  if (!hydrated) return <p className="text-muted">{t("common.loading")}</p>;

  if (!lines.length) {
    return (
      <div className="rounded-card bg-surface p-12 text-center shadow-soft">
        <BagIcon size={48} className="mx-auto text-primary-300" />
        <p className="mt-4 text-lg">{t("cart.empty")}</p>
        <Link href="/" className="btn btn-primary mt-6">
          {t("cart.empty_cta")}
        </Link>
      </div>
    );
  }

  const priced = new Map(quote?.items.map((i) => [i.item_code, i]) ?? []);

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
      <ul className="space-y-3" data-testid="cart-lines">
        {lines.map((line) => {
          const q = priced.get(line.item_code);
          return (
            <li key={line.item_code} className="flex gap-3 rounded-card bg-surface p-3 shadow-soft">
              <Link href={`/p/${encodeURIComponent(line.display.slug)}`} className="relative h-28 w-22 shrink-0 overflow-hidden rounded-xl bg-primary-50">
                <ProductImage src={line.display.image} alt={line.display.name} fill sizes="88px" className="object-cover" />
              </Link>
              <div className="flex flex-1 flex-col">
                <Link href={`/p/${encodeURIComponent(line.display.slug)}`} className="font-medium leading-6">
                  {line.display.name}
                </Link>
                {line.display.options.length > 0 && <p className="text-sm text-muted">{line.display.options.join(" / ")}</p>}
                <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                  <div className="flex items-center rounded-pill border border-line">
                    <button className="h-9 w-9 disabled:opacity-40" aria-label={t("product.decrease")} disabled={line.qty <= 1} onClick={() => setQty(line.item_code, line.qty - 1)}>
                      −
                    </button>
                    <span className="w-7 text-center text-sm font-semibold">{line.qty}</span>
                    <button className="h-9 w-9" aria-label={t("product.increase")} onClick={() => setQty(line.item_code, line.qty + 1)}>
                      +
                    </button>
                  </div>
                  <span className="font-semibold text-primary-700">{q ? formatPrice(q.amount, quote?.currency) : "…"}</span>
                </div>
              </div>
              <button className="self-start text-xs text-muted underline" onClick={() => remove(line.item_code)}>
                {t("cart.remove")}
              </button>
            </li>
          );
        })}
      </ul>

      <aside className="h-fit space-y-4 rounded-card bg-surface p-5 shadow-soft lg:sticky lg:top-24">
        <h2 className="font-heading text-xl font-bold">{t("checkout.summary")}</h2>
        {error && (
          <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <Summary quote={quote} showDelivery={false} loading={loading} />
        <p className="text-xs text-muted">{t("cart.delivery_note")}</p>
        <Link href="/checkout" className="btn btn-primary w-full" data-testid="go-checkout">
          {t("cart.checkout")}
        </Link>
        <Link href="/" className="block text-center text-sm text-primary-700">
          {t("cart.continue_shopping")}
        </Link>
      </aside>
    </div>
  );
}
