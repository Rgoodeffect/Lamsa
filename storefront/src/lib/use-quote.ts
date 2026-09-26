"use client";

import { useEffect, useRef, useState } from "react";

import { useCart } from "./cart-store";
import { errorMessage, postJson } from "./client-api";
import type { ApiError, Quote } from "./erp/types";

/**
 * Keeps a server quote in sync with the cart. Prices shown anywhere in the cart/checkout come
 * from here. Stock problems returned by the server are fixed in the cart automatically.
 */
export function useQuote(options: { zone?: string; giftWrap?: boolean } = {}) {
  const lines = useCart((s) => s.lines);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const key = JSON.stringify([lines.map((l) => [l.item_code, l.qty]), options.zone, options.giftWrap]);

  useEffect(() => {
    if (!lines.length) return;
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await postJson<Quote>(
          "/api/quote",
          { items: lines.map(({ item_code, qty }) => ({ item_code, qty })), zone: options.zone || undefined, gift_wrap: Boolean(options.giftWrap) },
          ctrl.signal,
        );
        if (res.ok) {
          setQuote(res.data);
          setError(null);
        } else {
          setError(errorMessage(res.error));
          fixCart(res.error);
        }
      } catch {
        /* aborted */
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` captures lines/options
  }, [key]);

  return { quote: lines.length ? quote : null, error: lines.length ? error : null, loading, lines };
}

/** Apply the server's stock/availability verdict to the local cart. */
function fixCart(err: ApiError) {
  const code = String(err.details?.item_code ?? "");
  if (!code) return;
  const { setQty, remove } = useCart.getState();
  if (err.code === "item_unavailable" || err.code === "variant_required") remove(code);
  if (err.code === "out_of_stock") {
    const available = Number(err.details?.available ?? 0);
    if (available > 0) setQty(code, available);
    else remove(code);
  }
  if (err.code === "qty_limit") setQty(code, Number(err.details?.max_qty ?? 1));
}
