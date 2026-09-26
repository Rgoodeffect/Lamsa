"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage, postJson } from "@/lib/client-api";
import type { OrderResult, PaymentVerification } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

/**
 * Moamalat Lightbox: the card form lives inside Moamalat's own iframe, so no card data ever
 * reaches Lamsa. The parameters (including the SecureHash) are built and signed by ERPNext.
 *
 * The widget hands its result to the browser, which cannot be trusted with it, so the result is
 * posted to /api/payment/moamalat and ERPNext decides whether the order is paid: it recomputes the
 * SecureHash with the merchant secret and checks the amount. `onPaid` only ever runs after that.
 */
type Phase = "loading" | "open" | "verifying" | "paid" | "failed" | "cancelled";

type LightboxConfigure = Record<string, unknown> & {
  completeCallback?: (data: Record<string, unknown>) => void;
  errorCallback?: (data: Record<string, unknown>) => void;
  cancelCallback?: () => void;
};

declare global {
  interface Window {
    Lightbox?: {
      Checkout: {
        configure: LightboxConfigure;
        showLightbox: () => void;
        closeLightbox: () => void;
      };
    };
  }
}

export function MoamalatLightbox({ order, onPaid }: { order: OrderResult; onPaid: () => void }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);
  const settled = useRef(false);

  const scriptUrl = order.payment.extra?.script_url;
  const params = order.payment.extra?.params;
  // Derived, not state: ERPNext either sent the widget parameters or it did not, and rendering that
  // from state would mean calling setState inside the effect below.
  const misconfigured = !scriptUrl || !params;

  const verify = useCallback(
    async (payload: Record<string, unknown>) => {
      if (settled.current) return;
      settled.current = true;
      setPhase("verifying");
      const res = await postJson<PaymentVerification>("/api/payment/moamalat", { payload });
      if (res.ok && res.data.status === "paid") {
        setPhase("paid");
        onPaid();
        return;
      }
      // The gateway may have taken the money even when this call fails, so never say "not paid":
      // the order page shows the status ERPNext holds.
      settled.current = false;
      setPhase("failed");
      setError(res.ok ? t("payment.failed") : errorMessage(res.error));
    },
    [onPaid],
  );

  useEffect(() => {
    if (!scriptUrl || !params) return;

    let cancelled = false;
    const open = () => {
      const checkout = window.Lightbox?.Checkout;
      if (cancelled || !checkout) {
        setPhase("failed");
        setError(t("payment.unavailable"));
        return;
      }
      checkout.configure = {
        ...params,
        completeCallback: (data) => void verify(data),
        errorCallback: (data) => {
          setPhase("failed");
          setError(String(data?.ErrorMessage || "") || t("payment.failed"));
        },
        cancelCallback: () => setPhase("cancelled"),
      };
      setPhase("open");
      checkout.showLightbox();
    };

    if (window.Lightbox?.Checkout) {
      open();
      return () => {
        cancelled = true;
      };
    }

    const script = document.createElement("script");
    script.src = scriptUrl;
    script.async = true;
    script.onload = open;
    script.onerror = () => {
      setPhase("failed");
      setError(t("payment.unavailable"));
    };
    document.body.append(script);
    return () => {
      cancelled = true;
    };
  }, [scriptUrl, params, verify]);

  const shownPhase: Phase = misconfigured ? "failed" : phase;
  const shownError = misconfigured ? t("payment.unavailable") : error;

  const retry = () => {
    setError(null);
    window.Lightbox?.Checkout.showLightbox();
    setPhase("open");
  };

  return (
    <div className="rounded-card bg-surface p-6 text-center shadow-soft" data-testid="moamalat-lightbox">
      <p className="font-heading text-lg font-bold">{t("payment.card_title")}</p>
      <p className="mt-2 text-muted">
        {shownPhase === "verifying"
          ? t("payment.verifying")
          : shownPhase === "paid"
            ? t("payment.paid")
            : shownPhase === "cancelled"
              ? t("payment.cancelled")
              : t("payment.opening")}
      </p>
      {shownError ? (
        <p role="alert" className="mt-3 text-danger">
          {shownError}
        </p>
      ) : null}
      {shownPhase === "failed" || shownPhase === "cancelled" ? (
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={retry} className="rounded-pill bg-primary-600 px-5 py-2.5 font-medium text-white">
            {t("payment.retry")}
          </button>
          <a href={`/order/${encodeURIComponent(order.order_no)}`} className="rounded-pill border border-line px-5 py-2.5 font-medium">
            {t("payment.show_order")}
          </a>
        </div>
      ) : null}
    </div>
  );
}
