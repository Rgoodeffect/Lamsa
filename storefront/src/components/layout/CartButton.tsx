"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { cartCount, useCart } from "@/lib/cart-store";
import { t } from "@/lib/i18n";

import { BagIcon } from "../Icons";

const subscribe = () => () => {};

export function CartButton() {
  const count = useCart((s) => cartCount(s.lines));
  // localStorage is only available after hydration
  const hydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const shown = hydrated ? count : 0;
  return (
    <Link
      href="/cart"
      className="relative rounded-full p-2.5 hover:bg-primary-50"
      aria-label={`${t("nav.cart")} (${shown})`}
      data-testid="cart-button"
    >
      <BagIcon />
      {shown > 0 && (
        <span className="absolute -top-0.5 -end-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-primary-600 px-1 text-xs font-bold text-white">
          {shown}
        </span>
      )}
    </Link>
  );
}
