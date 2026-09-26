"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";

import type { Facets } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

import { CloseIcon, FilterIcon } from "../Icons";

type Props = { facets: Facets; showAge: boolean; currencySymbol: string };

export function Filters({ facets, showAge, currencySymbol }: Props) {
  const [open, setOpen] = useState(false);
  const panel = <FilterPanel facets={facets} showAge={showAge} currencySymbol={currencySymbol} onDone={() => setOpen(false)} />;
  return (
    <>
      <button type="button" className="btn btn-outline py-2 lg:hidden" onClick={() => setOpen(true)} aria-expanded={open}>
        <FilterIcon size={18} />
        {t("filters.title")}
      </button>
      <aside className="hidden lg:block">{panel}</aside>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("filters.title")}>
          <button className="absolute inset-0 bg-ink/40" aria-label={t("nav.close")} onClick={() => setOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-3xl bg-cream p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-heading text-xl font-bold">{t("filters.title")}</h2>
              <button className="rounded-full p-2" aria-label={t("nav.close")} onClick={() => setOpen(false)}>
                <CloseIcon />
              </button>
            </div>
            {panel}
          </div>
        </div>
      )}
    </>
  );
}

function FilterPanel({ facets, showAge, currencySymbol, onDone }: Props & { onDone: () => void }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [min, setMin] = useState(params.get("min") ?? "");
  const [max, setMax] = useState(params.get("max") ?? "");

  const navigate = (next: URLSearchParams) => {
    next.delete("page");
    startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
  };

  const toggle = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    const values = next.getAll(key);
    next.delete(key);
    (values.includes(value) ? values.filter((v) => v !== value) : [...values, value]).forEach((v) => next.append(key, v));
    navigate(next);
  };

  const applyPrice = () => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of [["min", min], ["max", max]] as const) {
      if (value && Number(value) > 0) next.set(key, value);
      else next.delete(key);
    }
    navigate(next);
    onDone();
  };

  const selected = (key: string, value: string) => params.getAll(key).includes(value);

  return (
    <div className={`space-y-6 ${pending ? "opacity-60" : ""}`} data-testid="filters">
      {facets.sizes.length > 0 && (
        <fieldset>
          <legend className="mb-2 font-semibold">{t("filters.size")}</legend>
          <div className="flex flex-wrap gap-2">
            {facets.sizes.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={selected("size", s)}
                onClick={() => toggle("size", s)}
                className="min-w-11 rounded-xl border border-line bg-surface px-3 py-2 text-sm aria-pressed:border-primary-500 aria-pressed:bg-primary-50 aria-pressed:text-primary-700"
              >
                {s}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {facets.colors.length > 0 && (
        <fieldset>
          <legend className="mb-2 font-semibold">{t("filters.color")}</legend>
          <div className="flex flex-wrap gap-2">
            {facets.colors.map((c) => (
              <button
                key={c.name}
                type="button"
                aria-pressed={selected("color", c.name)}
                onClick={() => toggle("color", c.name)}
                className="flex items-center gap-2 rounded-pill border border-line bg-surface px-3 py-1.5 text-sm aria-pressed:border-primary-500 aria-pressed:bg-primary-50"
              >
                <span className="h-4 w-4 rounded-full border border-line" style={{ background: c.swatch ?? "var(--color-accent-200)" }} />
                {c.name}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {showAge && facets.age_ranges.length > 0 && (
        <fieldset>
          <legend className="mb-2 font-semibold">{t("filters.age")}</legend>
          <div className="flex flex-wrap gap-2">
            {facets.age_ranges.map((a) => (
              <button
                key={a.name}
                type="button"
                aria-pressed={selected("age", a.name)}
                onClick={() => toggle("age", a.name)}
                className="rounded-pill border border-line bg-surface px-3 py-1.5 text-sm aria-pressed:border-primary-500 aria-pressed:bg-primary-50"
              >
                {a.label}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <fieldset>
        <legend className="mb-2 font-semibold">
          {t("filters.price")} <span className="text-xs font-normal text-muted">({currencySymbol})</span>
        </legend>
        <div className="flex items-center gap-2">
          <input
            className="field"
            inputMode="numeric"
            placeholder={`${t("filters.price_min")} ${Math.floor(facets.price.min)}`}
            aria-label={t("filters.price_min")}
            value={min}
            onChange={(e) => setMin(e.target.value.replace(/\D/g, ""))}
          />
          <input
            className="field"
            inputMode="numeric"
            placeholder={`${t("filters.price_max")} ${Math.ceil(facets.price.max)}`}
            aria-label={t("filters.price_max")}
            value={max}
            onChange={(e) => setMax(e.target.value.replace(/\D/g, ""))}
          />
          <button type="button" className="btn btn-outline px-4 py-2.5" onClick={applyPrice}>
            {t("filters.apply")}
          </button>
        </div>
      </fieldset>

      <label className="flex cursor-pointer items-center gap-3">
        <input
          type="checkbox"
          className="h-5 w-5 accent-primary-600"
          checked={params.get("stock") === "1"}
          onChange={() => {
            const next = new URLSearchParams(params.toString());
            if (next.get("stock") === "1") next.delete("stock");
            else next.set("stock", "1");
            navigate(next);
          }}
        />
        {t("filters.in_stock")}
      </label>

      <button type="button" className="btn btn-primary w-full lg:hidden" onClick={onDone}>
        {t("filters.show_results")}
      </button>
    </div>
  );
}
