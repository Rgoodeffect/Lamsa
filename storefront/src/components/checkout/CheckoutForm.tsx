"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import { newEventId, trackPixel } from "@/lib/analytics/pixel";
import { useCart } from "@/lib/cart-store";
import { errorMessage, postJson } from "@/lib/client-api";
import type { OrderResult, StoreConfig, Zones } from "@/lib/erp/types";
import { formatPrice } from "@/lib/format";
import { type MessageKey, t } from "@/lib/i18n";
import { isValidLibyanPhone } from "@/lib/phone";
import { useQuote } from "@/lib/use-quote";

import { CouponField } from "../cart/CouponField";
import { Summary } from "../cart/Summary";
import { GiftIcon } from "../Icons";
import { MoamalatLightbox } from "./MoamalatLightbox";

const noop = () => () => {};
export const ORDER_STORAGE_PREFIX = "lamsa-order:";

type Errors = Partial<Record<"full_name" | "phone" | "city" | "zone", string>>;

export function CheckoutForm({ zones, config }: { zones: Zones; config: StoreConfig }) {
  const router = useRouter();
  const hydrated = useSyncExternalStore(noop, () => true, () => false);
  const clear = useCart((s) => s.clear);

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [zone, setZone] = useState("");
  const [notes, setNotes] = useState("");
  const [giftWrap, setGiftWrap] = useState(false);
  const [giftMessage, setGiftMessage] = useState("");
  const [provider, setProvider] = useState(config.payment_providers[0]?.code ?? "cod");
  const [errors, setErrors] = useState<Errors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Set when an online provider needs the customer to pay before we leave the page.
  const [payingFor, setPayingFor] = useState<OrderResult | null>(null);
  // one id per checkout attempt: idempotency key for ERPNext + Pixel/CAPI dedup id
  const eventId = useRef<string>("");

  const { quote, error: quoteError, couponError, loading, lines } = useQuote({ zone, giftWrap });
  const areas = useMemo(() => zones.cities.find((c) => c.city === city)?.areas ?? [], [zones, city]);
  const selectedArea = areas.find((a) => a.zone === zone);

  const initiated = useRef(false);
  useEffect(() => {
    if (!quote || initiated.current) return;
    initiated.current = true;
    trackPixel("InitiateCheckout", {
      content_ids: quote.items.map((i) => i.item_code),
      num_items: quote.items.reduce((s, i) => s + i.qty, 0),
      value: quote.grand_total,
      currency: quote.currency,
    });
  }, [quote]);

  if (!hydrated) return <p className="mt-6 text-muted">{t("common.loading")}</p>;
  // Must come before the empty-cart branch: that branch would otherwise win the moment the cart is
  // emptied and show "your cart is empty" instead of the payment window, stranding an unpaid order.
  if (payingFor) {
    return (
      <MoamalatLightbox
        order={payingFor}
        onPaid={() => {
          clear();
          router.push(`/order/${encodeURIComponent(payingFor.order_no)}`);
        }}
      />
    );
  }
  if (!lines.length) {
    return (
      <div className="mt-6 rounded-card bg-surface p-10 text-center">
        <p>{t("cart.empty")}</p>
        <Link href="/" className="btn btn-primary mt-4">
          {t("cart.empty_cta")}
        </Link>
      </div>
    );
  }

  const validate = (): Errors => {
    const e: Errors = {};
    if (fullName.trim().length < 2) e.full_name = t("errors.invalid_name");
    if (!isValidLibyanPhone(phone)) e.phone = t("errors.invalid_phone");
    if (!city) e.city = t("checkout.required");
    if (!zone) e.zone = t("errors.invalid_zone");
    return e;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) {
      document.querySelector<HTMLElement>("[aria-invalid=true]")?.focus();
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    eventId.current ||= newEventId();
    const res = await postJson<OrderResult>("/api/checkout", {
      items: lines.map(({ item_code, qty }) => ({ item_code, qty })),
      full_name: fullName.trim(),
      phone,
      zone,
      address_notes: notes.trim(),
      gift_wrap: giftWrap,
      gift_message: giftWrap ? giftMessage.trim() : "",
      payment_provider: provider,
      coupon_code: useCart.getState().couponCode || undefined,
      event_id: eventId.current,
    });
    if (!res.ok) {
      setSubmitting(false);
      setSubmitError(errorMessage(res.error));
      if (["invalid_event_id"].includes(res.error.code)) eventId.current = "";
      return;
    }
    const order = res.data;
    try {
      sessionStorage.setItem(ORDER_STORAGE_PREFIX + order.order_no, JSON.stringify({ ...order, phone }));
    } catch {
      /* private mode: the confirmation page falls back to tracking */
    }
    if (order.payment.status === "lightbox") {
      // The order exists as a draft but is not paid until ERPNext verifies the gateway's response,
      // so the cart stays as it is: if the payment fails the customer can retry or switch to cash.
      setPayingFor(order);
      return;
    }
    clear();
    if (order.payment.status === "redirect" && order.payment.redirect_url) {
      window.location.assign(order.payment.redirect_url);
      return;
    }
    router.push(`/order/${encodeURIComponent(order.order_no)}`);
  };

  const field = (name: keyof Errors) => ({
    "aria-invalid": errors[name] ? true : undefined,
    "aria-describedby": errors[name] ? `${name}-error` : undefined,
  });
  const fieldError = (name: keyof Errors) =>
    errors[name] ? (
      <p id={`${name}-error`} className="mt-1 text-sm text-danger">
        {errors[name]}
      </p>
    ) : null;

  return (
    <form onSubmit={submit} noValidate className="mt-6 grid gap-8 lg:grid-cols-[1fr_24rem]" data-testid="checkout-form">
      <div className="space-y-6">
        <section className="space-y-4 rounded-card bg-surface p-5 shadow-soft">
          <h2 className="font-heading text-xl font-bold">{t("checkout.contact")}</h2>
          <div>
            <label htmlFor="full_name" className="mb-1 block font-medium">
              {t("checkout.full_name")}
            </label>
            <input id="full_name" name="full_name" className="field" autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={140} {...field("full_name")} />
            {fieldError("full_name")}
          </div>
          <div>
            <label htmlFor="phone" className="mb-1 block font-medium">
              {t("checkout.phone")}
            </label>
            <input
              id="phone"
              name="phone"
              className="field text-start"
              dir="ltr"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder={t("checkout.phone_hint")}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              maxLength={20}
              {...field("phone")}
            />
            {fieldError("phone")}
          </div>
        </section>

        <section className="space-y-4 rounded-card bg-surface p-5 shadow-soft">
          <h2 className="font-heading text-xl font-bold">{t("checkout.delivery")}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="city" className="mb-1 block font-medium">
                {t("checkout.city")}
              </label>
              <select
                id="city"
                className="field"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setZone("");
                }}
                {...field("city")}
              >
                <option value="">{t("checkout.select_city")}</option>
                {zones.cities.map((c) => (
                  <option key={c.city} value={c.city}>
                    {c.city}
                  </option>
                ))}
              </select>
              {fieldError("city")}
            </div>
            <div>
              <label htmlFor="zone" className="mb-1 block font-medium">
                {t("checkout.area")}
              </label>
              <select id="zone" className="field" value={zone} onChange={(e) => setZone(e.target.value)} disabled={!city} {...field("zone")}>
                <option value="">{t("checkout.select_area")}</option>
                {areas.map((a) => (
                  <option key={a.zone} value={a.zone}>
                    {a.area} — {formatPrice(a.fee, config.currency)}
                  </option>
                ))}
              </select>
              {fieldError("zone")}
            </div>
          </div>
          {selectedArea && (
            <p className="text-sm text-success">
              {selectedArea.est_days_max > selectedArea.est_days_min
                ? t("checkout.eta", { min: selectedArea.est_days_min, max: selectedArea.est_days_max })
                : t("checkout.eta_single", { days: selectedArea.est_days_max })}
            </p>
          )}
          <div>
            <label htmlFor="notes" className="mb-1 block font-medium">
              {t("checkout.address_notes")}
            </label>
            <textarea id="notes" className="field min-h-24" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} autoComplete="street-address" />
          </div>
        </section>

        {config.gift_wrap.enabled && (
          <section className="space-y-3 rounded-card border border-accent-200 bg-accent-50 p-5">
            <h2 className="flex items-center gap-2 font-heading text-xl font-bold">
              <GiftIcon className="text-accent-600" /> {t("checkout.gift")}
            </h2>
            <label className="flex cursor-pointer items-center gap-3">
              <input type="checkbox" className="h-5 w-5 accent-primary-600" checked={giftWrap} onChange={(e) => setGiftWrap(e.target.checked)} data-testid="gift-wrap" />
              {t("checkout.gift_wrap", { fee: formatPrice(config.gift_wrap.fee, config.currency) })}
            </label>
            {giftWrap && (
              <div>
                <label htmlFor="gift_message" className="mb-1 block font-medium">
                  {t("checkout.gift_message")}
                </label>
                <textarea
                  id="gift_message"
                  className="field min-h-20"
                  value={giftMessage}
                  onChange={(e) => setGiftMessage(e.target.value)}
                  maxLength={config.gift_wrap.message_max_length}
                />
                <p className="mt-1 flex justify-between text-xs text-muted">
                  <span>{t("checkout.gift_message_hint")}</span>
                  <span dir="ltr">
                    {giftMessage.length}/{config.gift_wrap.message_max_length}
                  </span>
                </p>
              </div>
            )}
          </section>
        )}

        <section className="space-y-3 rounded-card bg-surface p-5 shadow-soft">
          <h2 className="font-heading text-xl font-bold">{t("checkout.payment")}</h2>
          {config.payment_providers.map((p) => (
            <label key={p.code} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-3 has-[:checked]:border-primary-400 has-[:checked]:bg-primary-50">
              <input type="radio" name="payment" className="mt-1.5 accent-primary-600" value={p.code} checked={provider === p.code} onChange={() => setProvider(p.code)} />
              <span>
                <span className="block font-medium">{t(p.label_key as MessageKey)}</span>
                {p.code === "cod" && <span className="block text-sm text-muted">{t("payment.cod_note")}</span>}
              </span>
            </label>
          ))}
        </section>
      </div>

      <aside className="h-fit space-y-4 rounded-card bg-surface p-5 shadow-soft lg:sticky lg:top-24">
        <h2 className="font-heading text-xl font-bold">{t("checkout.summary")}</h2>
        <ul className="space-y-2 text-sm">
          {lines.map((l) => (
            <li key={l.item_code} className="flex justify-between gap-2">
              <span>
                {l.display.name}
                {l.display.options.length > 0 && <span className="text-muted"> ({l.display.options.join(" / ")})</span>} × {l.qty}
              </span>
            </li>
          ))}
        </ul>
        <CouponField applied={quote?.coupon ?? null} error={couponError} currency={quote?.currency ?? ""} />
        <Summary quote={quote} showDelivery loading={loading} />
        {(submitError || quoteError) && (
          <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert" data-testid="checkout-error">
            {submitError || quoteError}
          </p>
        )}
        <button type="submit" className="btn btn-primary w-full py-3.5 text-lg" disabled={submitting || !quote} data-testid="place-order">
          {submitting ? t("checkout.placing") : t("checkout.place_order")}
        </button>
      </aside>
    </form>
  );
}
