"use client";

import { useState } from "react";

import { useCart } from "@/lib/cart-store";
import type { AppliedCoupon } from "@/lib/erp/types";
import { formatPrice } from "@/lib/format";
import { t } from "@/lib/i18n";

/**
 * Coupon entry. The code is all the browser holds: whether it is valid, and what it is worth, comes
 * back from the server quote — so editing it here can never change what the customer is charged.
 */
export function CouponField({
  applied,
  error,
  currency,
}: {
  applied: AppliedCoupon | null;
  error: string | null;
  currency: string;
}) {
  const savedCode = useCart((s) => s.couponCode);
  const setCouponCode = useCart((s) => s.setCouponCode);
  const [draft, setDraft] = useState(savedCode);

  if (applied) {
    return (
      <div className="rounded-xl bg-success/10 p-3 text-sm" data-testid="coupon-applied">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-success">
            {t("coupon.applied").replace("{percent}", String(applied.percent))}
          </span>
          <button
            type="button"
            onClick={() => {
              setCouponCode("");
              setDraft("");
            }}
            className="text-muted underline hover:text-danger"
          >
            {t("coupon.remove")}
          </button>
        </div>
        <p className="mt-1 text-muted" dir="ltr">
          {applied.code}
        </p>
        <p className="mt-1 font-medium">
          {t("coupon.saved").replace("{amount}", formatPrice(applied.discount, currency))}
        </p>
      </div>
    );
  }

  return (
    <div className="text-sm">
      <label htmlFor="coupon" className="mb-1 block font-medium">
        {t("coupon.label")}
      </label>
      <div className="flex gap-2">
        <input
          id="coupon"
          name="coupon"
          value={draft}
          onChange={(e) => setDraft(e.target.value.toUpperCase())}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              setCouponCode(draft);
            }
          }}
          dir="ltr"
          autoComplete="off"
          spellCheck={false}
          placeholder={t("coupon.placeholder")}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "coupon-error" : undefined}
          className="min-w-0 flex-1 rounded-xl border border-line bg-surface px-3 py-2"
          data-testid="coupon-input"
        />
        <button
          type="button"
          onClick={() => setCouponCode(draft)}
          disabled={!draft.trim()}
          className="btn btn-outline shrink-0 disabled:opacity-50"
          data-testid="coupon-apply"
        >
          {t("coupon.apply")}
        </button>
      </div>
      {error ? (
        <p id="coupon-error" role="alert" className="mt-1 text-danger" data-testid="coupon-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
