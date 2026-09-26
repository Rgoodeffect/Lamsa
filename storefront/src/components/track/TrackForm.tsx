"use client";

import { useState } from "react";

import { errorMessage, postJson } from "@/lib/client-api";
import type { TrackResult } from "@/lib/erp/types";
import { formatDate, formatPrice } from "@/lib/format";
import { t, tDynamic } from "@/lib/i18n";

export function TrackForm({ initialOrderNo }: { initialOrderNo: string }) {
  const [orderNo, setOrderNo] = useState(initialOrderNo);
  const [phone, setPhone] = useState("");
  const [result, setResult] = useState<TrackResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderNo.trim() || !phone.trim()) {
      setError(t("checkout.required"));
      return;
    }
    setLoading(true);
    setError(null);
    const res = await postJson<TrackResult>("/api/track", { order_no: orderNo.trim(), phone });
    setLoading(false);
    if (res.ok) setResult(res.data);
    else {
      setResult(null);
      setError(errorMessage(res.error));
    }
  };

  return (
    <div className="mt-6 space-y-6">
      <form onSubmit={submit} className="space-y-4 rounded-card bg-surface p-5 shadow-soft" data-testid="track-form">
        <div>
          <label htmlFor="order_no" className="mb-1 block font-medium">
            {t("track.order_no")}
          </label>
          <input id="order_no" className="field" dir="ltr" value={orderNo} onChange={(e) => setOrderNo(e.target.value)} maxLength={30} />
        </div>
        <div>
          <label htmlFor="track_phone" className="mb-1 block font-medium">
            {t("track.phone")}
          </label>
          <input id="track_phone" className="field" dir="ltr" type="tel" inputMode="tel" placeholder={t("checkout.phone_hint")} value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={20} />
        </div>
        {error && (
          <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-primary w-full" disabled={loading}>
          {loading ? t("common.loading") : t("track.submit")}
        </button>
      </form>

      {result && (
        <section className="rounded-card bg-surface p-5 shadow-soft" aria-live="polite" data-testid="track-result">
          <div className="flex items-baseline justify-between">
            <p className="font-heading text-xl font-bold" dir="ltr">
              {result.order_no}
            </p>
            <p className="text-sm text-muted">
              {t("track.placed_on")}: {formatDate(result.placed_on)}
            </p>
          </div>
          <p className="mt-2">
            {t("track.status")}: <strong data-testid="track-status">{tDynamic(`status.${result.status}`, "track.status")}</strong>
          </p>
          {result.step_index >= 0 && (
            <ol className="mt-5 grid grid-cols-4 gap-2 text-center text-xs">
              {result.steps.map((step, i) => (
                <li key={step} className="space-y-2">
                  <span className={`block h-1.5 rounded-full ${i <= result.step_index ? "bg-primary-500" : "bg-line"}`} />
                  <span className={i <= result.step_index ? "font-semibold text-primary-700" : "text-muted"}>
                    {tDynamic(`status.${step}`, "track.status")}
                  </span>
                </li>
              ))}
            </ol>
          )}
          <ul className="mt-5 space-y-1 border-t border-line pt-4 text-sm">
            {result.items.map((i) => (
              <li key={i.item_code} className="flex justify-between">
                <span>
                  {i.name} × {i.qty}
                </span>
                <span>{formatPrice(i.amount, result.currency)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 flex justify-between font-bold">
            <span>{t("checkout.total")}</span>
            <span>{formatPrice(result.grand_total, result.currency)}</span>
          </p>
        </section>
      )}
    </div>
  );
}
