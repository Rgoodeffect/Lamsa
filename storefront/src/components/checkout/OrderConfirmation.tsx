"use client";

import Link from "next/link";
import { useEffect, useSyncExternalStore } from "react";

import { trackPixel } from "@/lib/analytics/pixel";
import type { OrderResult } from "@/lib/erp/types";
import { formatPrice } from "@/lib/format";
import { t } from "@/lib/i18n";

import { CheckIcon } from "../Icons";
import { ORDER_STORAGE_PREFIX } from "./CheckoutForm";

type Stored = OrderResult & { phone?: string };
const noop = () => () => {};

function readOrder(orderNo: string): string | null {
  try {
    return sessionStorage.getItem(ORDER_STORAGE_PREFIX + orderNo);
  } catch {
    return null;
  }
}

export function OrderConfirmation({ orderNo }: { orderNo: string }) {
  const raw = useSyncExternalStore(noop, () => readOrder(orderNo), () => null);
  const order: Stored | null = raw ? JSON.parse(raw) : null;

  useEffect(() => {
    if (!order) return;
    const firedKey = `${ORDER_STORAGE_PREFIX}pixel:${order.order_no}`;
    try {
      if (sessionStorage.getItem(firedKey)) return;
      sessionStorage.setItem(firedKey, "1");
    } catch {
      /* ignore */
    }
    // eventID matches the server-side CAPI event so Meta counts the purchase once
    trackPixel(
      "Purchase",
      {
        content_ids: order.items.map((i) => i.item_code),
        contents: order.items.map((i) => ({ id: i.item_code, quantity: i.qty, item_price: i.rate })),
        content_type: "product",
        value: order.grand_total,
        currency: order.currency,
        num_items: order.items.reduce((s, i) => s + i.qty, 0),
      },
      order.event_id,
    );
  }, [order]);

  return (
    <div className="mx-auto max-w-xl rounded-card bg-surface p-6 text-center shadow-soft md:p-10" data-testid="order-confirmation">
      <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-success/10 text-success">
        <CheckIcon size={34} />
      </span>
      <h1 className="mt-4 font-heading text-2xl font-bold md:text-3xl">{t("order.thanks")}</h1>
      <p className="mt-4 text-muted">{t("order.number")}</p>
      <p className="font-heading text-3xl font-bold tracking-wider text-primary-700" dir="ltr" data-testid="order-number">
        {orderNo}
      </p>
      <p className="mt-2 text-sm text-muted">{t("order.save_number")}</p>

      {order ? (
        <div className="mt-6 space-y-2 rounded-xl bg-cream p-4 text-start text-sm">
          <p className="font-semibold">{t("order.items")}</p>
          <ul className="space-y-1">
            {order.items.map((i) => (
              <li key={i.item_code} className="flex justify-between">
                <span>
                  {i.name} × {i.qty}
                </span>
                <span>{formatPrice(i.amount, order.currency)}</span>
              </li>
            ))}
          </ul>
          <p className="flex justify-between border-t border-line pt-2 text-base font-bold">
            <span>{t("order.total_cod")}</span>
            <span>{formatPrice(order.grand_total, order.currency)}</span>
          </p>
        </div>
      ) : (
        <p className="mt-6 rounded-xl bg-cream p-4 text-sm text-muted">{t("order.not_found_local")}</p>
      )}

      <p className="mt-6">{t("order.next_steps")}</p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link href={`/track?order=${encodeURIComponent(orderNo)}`} className="btn btn-primary">
          {t("order.track_cta")}
        </Link>
        <Link href="/" className="btn btn-outline">
          {t("order.continue")}
        </Link>
      </div>
    </div>
  );
}
