"use client";

import { useEffect, useRef, useState } from "react";

import type { ImageMatch } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

import { ProductGrid } from "./ProductCard";

/**
 * Search by photo: pick a file, or paste an image straight into the page.
 *
 * The photo goes to the server, is compared against the product images there and is not stored.
 * The server decides what matches — ranking never happens in the browser.
 */
const MAX_BYTES = 8 * 1024 * 1024;

type State =
  | { phase: "idle" }
  | { phase: "searching" }
  | { phase: "done"; products: ImageMatch[]; currency: string }
  | { phase: "error"; message: string };

export function ImageSearch({ currency }: { currency: string }) {
  const [state, setState] = useState<State>({ phase: "idle" });
  const [preview, setPreview] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  // Revoke the preview URL when it changes or the component goes away.
  useEffect(() => {
    if (!preview) return;
    return () => URL.revokeObjectURL(preview);
  }, [preview]);

  const run = async (file: File) => {
    if (file.size > MAX_BYTES) {
      setState({ phase: "error", message: t("image_search.too_large") });
      return;
    }
    setPreview(URL.createObjectURL(file));
    setState({ phase: "searching" });

    const body = new FormData();
    body.append("image", file);
    try {
      const res = await fetch("/api/search-by-image", { method: "POST", body });
      const payload = await res.json().catch(() => null);
      if (!res.ok || !payload?.ok) {
        const code = payload?.error?.code as string | undefined;
        setState({ phase: "error", message: messageFor(code) });
        return;
      }
      setState({ phase: "done", products: payload.data.products, currency });
    } catch {
      setState({ phase: "error", message: t("image_search.failed") });
    }
  };

  // Paste anywhere on the page: the quickest way in on a phone or a laptop.
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const file = [...(event.clipboardData?.items ?? [])]
        .find((item) => item.kind === "file" && item.type.startsWith("image/"))
        ?.getAsFile();
      if (file) void run(file);
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `run` is stable enough for a listener
  }, []);

  const reset = () => {
    setState({ phase: "idle" });
    setPreview(null);
    if (input.current) input.current.value = "";
  };

  return (
    <section className="mt-6" data-testid="image-search">
      <div className="rounded-card bg-surface p-4">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => input.current?.click()}
            className="btn btn-outline"
            data-testid="image-search-pick"
          >
            {t("image_search.cta")}
          </button>
          <p className="text-sm text-muted">{t("image_search.hint")}</p>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif,image/gif"
            className="sr-only"
            aria-label={t("image_search.cta")}
            data-testid="image-search-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void run(file);
            }}
          />
        </div>

        {preview ? (
          <div className="mt-4 flex items-center gap-3">
            {/* the shopper's own file, not a catalog image: a plain img is right here */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt={t("image_search.your_photo")} className="h-20 w-20 rounded-xl object-cover" />
            <button type="button" onClick={reset} className="text-sm text-muted underline hover:text-danger">
              {t("image_search.clear")}
            </button>
          </div>
        ) : null}

        {state.phase === "searching" ? (
          <p className="mt-4 text-muted" data-testid="image-search-loading">
            {t("image_search.searching")}
          </p>
        ) : null}

        {state.phase === "error" ? (
          <p role="alert" className="mt-4 text-danger" data-testid="image-search-error">
            {state.message}
          </p>
        ) : null}
      </div>

      {state.phase === "done" ? (
        state.products.length ? (
          <div className="mt-6">
            <h2 className="mb-3 font-heading text-xl font-bold">{t("image_search.results")}</h2>
            <ProductGrid products={state.products} currency={state.currency} />
          </div>
        ) : (
          <p className="mt-6 rounded-card bg-surface p-10 text-center text-muted" data-testid="image-search-empty">
            {t("image_search.no_results")}
          </p>
        )
      ) : null}
    </section>
  );
}

function messageFor(code: string | undefined): string {
  switch (code) {
    case "image_too_large":
      return t("image_search.too_large");
    case "image_unreadable":
      return t("image_search.unreadable");
    case "image_search_unavailable":
      return t("image_search.unavailable");
    case "rate_limited":
      return t("errors.rate_limited");
    default:
      return t("image_search.failed");
  }
}
