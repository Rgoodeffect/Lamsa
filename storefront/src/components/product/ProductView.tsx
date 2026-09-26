"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { trackPixel } from "@/lib/analytics/pixel";
import { useCart } from "@/lib/cart-store";
import type { ProductDetail, Variant } from "@/lib/erp/types";
import { t } from "@/lib/i18n";
import { whatsappLink } from "@/lib/whatsapp";

import { CashIcon, CheckIcon, WhatsAppIcon } from "../Icons";
import { Price } from "../Price";
import { Gallery } from "./Gallery";
import { SizeGuideButton } from "./SizeGuide";

type Props = {
  product: ProductDetail;
  currency: string;
  whatsapp: string | null;
  productUrl: string;
};

export function ProductView({ product, currency, whatsapp, productUrl }: Props) {
  const hasSizes = product.sizes.length > 0;
  const hasColors = product.colors.length > 0;
  const variants = product.variants;

  const firstInStock = variants.find((v) => v.stock.status !== "out");
  const [size, setSize] = useState<string | null>(
    hasSizes && product.sizes.length === 1 ? product.sizes[0] : null,
  );
  const [color, setColor] = useState<string | null>(
    hasColors && product.colors.length === 1 ? product.colors[0].name : (firstInStock?.color ?? null),
  );
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const add = useCart((s) => s.add);

  const variant: Variant | null = useMemo(() => {
    if (!product.has_variants) return null;
    return (
      variants.find((v) => (!hasSizes || v.size === size) && (!hasColors || v.color === color)) ?? null
    );
  }, [variants, product.has_variants, hasSizes, hasColors, size, color]);

  const needsSelection = Boolean(product.has_variants) && ((hasSizes && !size) || (hasColors && !color));
  const stock = product.has_variants ? variant?.stock : product.stock;
  const unavailable = Boolean(product.has_variants) && !needsSelection && !variant;
  const canAdd = !needsSelection && !unavailable && stock?.status !== "out" && (stock?.max_qty ?? 0) > 0;
  const maxQty = stock?.max_qty ?? 1;

  useEffect(() => {
    trackPixel("ViewContent", {
      content_ids: [product.code],
      content_type: product.has_variants ? "product_group" : "product",
      content_name: product.name,
      value: product.min_price,
      currency,
    });
  }, [product.code, product.has_variants, product.name, product.min_price, currency]);

  // switching variant can lower the available quantity
  const quantity = Math.min(qty, Math.max(1, maxQty));

  const sizeAvailable = (s: string) =>
    variants.some((v) => v.size === s && (!hasColors || !color || v.color === color) && v.stock.status !== "out");
  const colorAvailable = (c: string) =>
    variants.some((v) => v.color === c && (!hasSizes || !size || v.size === size) && v.stock.status !== "out");

  const options = [size, color].filter(Boolean).join(" / ");

  const handleAdd = () => {
    const itemCode = variant?.code ?? product.code;
    if (!canAdd) return;
    add(
      {
        item_code: itemCode,
        qty: quantity,
        display: {
          name: product.name,
          slug: product.slug,
          image: variant?.image ?? product.images[0] ?? null,
          options: [size, color].filter(Boolean) as string[],
        },
      },
      maxQty,
    );
    trackPixel("AddToCart", {
      content_ids: [itemCode],
      content_type: "product",
      contents: [{ id: itemCode, quantity, item_price: variant?.price ?? product.min_price }],
      value: (variant?.price ?? product.min_price) * quantity,
      currency,
    });
    setAdded(true);
  };

  const waHref = whatsappLink(
    whatsapp,
    t("product.whatsapp_message", { name: product.name, options: options || "", url: productUrl }),
  );

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <Gallery images={product.images} alt={product.name} />

      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="font-heading text-3xl font-bold leading-snug">{product.name}</h1>
          <div className="text-2xl" data-testid="product-price">
            {variant ? (
              <Price min={variant.price} listMin={variant.list_price} currency={currency} />
            ) : (
              <Price
                min={product.min_price}
                max={product.max_price}
                listMin={product.list_min_price}
                listMax={product.list_max_price}
                currency={currency}
              />
            )}
          </div>
          <StockBadge status={needsSelection ? null : unavailable ? "out" : (stock?.status ?? null)} left={stock?.left} />
        </div>

        {hasColors && (
          <fieldset>
            <legend className="mb-2 font-semibold">
              {t("filters.color")}: <span className="font-normal text-muted">{color ?? t("product.choose_color")}</span>
            </legend>
            <div className="flex flex-wrap gap-2">
              {product.colors.map((c) => (
                <button
                  key={c.name}
                  type="button"
                  aria-pressed={color === c.name}
                  onClick={() => {
                    setColor(c.name);
                    setAdded(false);
                  }}
                  className={`flex items-center gap-2 rounded-pill border px-3 py-2 text-sm transition aria-pressed:border-primary-500 aria-pressed:bg-primary-50 ${
                    colorAvailable(c.name) ? "border-line" : "border-dashed border-line opacity-50"
                  }`}
                >
                  <span className="h-5 w-5 rounded-full border border-line" style={{ background: c.swatch ?? "var(--color-accent-200)" }} />
                  {c.name}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {hasSizes && (
          <fieldset>
            <div className="mb-2 flex items-center justify-between">
              <legend className="font-semibold">
                {t("filters.size")}: <span className="font-normal text-muted">{size ?? t("product.choose_size")}</span>
              </legend>
              {product.size_guide && <SizeGuideButton guide={product.size_guide} />}
            </div>
            <div className="flex flex-wrap gap-2">
              {product.sizes.map((sz) => (
                <button
                  key={sz}
                  type="button"
                  aria-pressed={size === sz}
                  onClick={() => {
                    setSize(sz);
                    setAdded(false);
                  }}
                  className={`min-w-12 rounded-xl border px-3 py-2.5 text-sm font-medium transition aria-pressed:border-primary-600 aria-pressed:bg-primary-600 aria-pressed:text-white ${
                    sizeAvailable(sz) ? "border-line bg-surface" : "border-dashed border-line bg-surface text-muted line-through"
                  }`}
                >
                  {sz}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <div className="flex items-center gap-3">
          <span className="font-semibold">{t("product.quantity")}</span>
          <div className="flex items-center rounded-pill border border-line bg-surface">
            <button
              type="button"
              className="h-11 w-11 text-xl disabled:opacity-40"
              onClick={() => setQty(Math.max(1, quantity - 1))}
              disabled={quantity <= 1}
              aria-label={t("product.decrease")}
            >
              −
            </button>
            <span className="w-8 text-center font-semibold" aria-live="polite">
              {quantity}
            </span>
            <button
              type="button"
              className="h-11 w-11 text-xl disabled:opacity-40"
              onClick={() => setQty(Math.min(maxQty, quantity + 1))}
              disabled={quantity >= maxQty}
              aria-label={t("product.increase")}
            >
              +
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <button type="button" className="btn btn-primary w-full py-3.5 text-lg" onClick={handleAdd} disabled={!canAdd} data-testid="add-to-cart">
            {needsSelection
              ? t("product.select_options")
              : unavailable
                ? t("product.unavailable_combination")
                : stock?.status === "out"
                  ? t("product.out_of_stock")
                  : t("product.add_to_cart")}
          </button>
          {added && (
            <p className="flex items-center justify-between rounded-xl bg-success/10 px-4 py-3 text-sm text-success" role="status">
              <span className="flex items-center gap-2">
                <CheckIcon size={18} /> {t("product.added_to_cart")}
              </span>
              <Link href="/cart" className="font-semibold underline">
                {t("product.view_cart")}
              </Link>
            </p>
          )}
          {waHref && (
            <a href={waHref} target="_blank" rel="noopener noreferrer" className="btn w-full border border-[#25D366] text-[#128C7E] hover:bg-[#25D366]/10" data-testid="order-whatsapp">
              <WhatsAppIcon size={22} />
              {t("product.order_whatsapp")}
            </a>
          )}
          <p className="flex items-center gap-2 text-sm text-muted">
            <CashIcon size={18} /> {t("product.cod_note")}
          </p>
        </div>

        {product.description && (
          <section>
            <h2 className="mb-2 font-heading text-xl font-bold">{t("product.description")}</h2>
            {/* Description HTML comes from ERPNext's Text Editor field (sanitized by Frappe on save). */}
            <div className="prose-sm leading-8 text-ink/90 [&_li]:ms-5 [&_ul]:list-disc" dangerouslySetInnerHTML={{ __html: product.description }} />
          </section>
        )}
      </div>
    </div>
  );
}

function StockBadge({ status, left }: { status: "in" | "low" | "out" | null; left?: number }) {
  if (!status) return null;
  const styles = {
    in: "bg-success/10 text-success",
    low: "bg-warning/10 text-warning",
    out: "bg-ink/10 text-muted",
  };
  const label =
    status === "in" ? t("product.in_stock") : status === "low" ? t("product.low_stock", { left: left ?? 1 }) : t("product.out_of_stock");
  return (
    <span className={`inline-block rounded-pill px-3 py-1 text-xs font-semibold ${styles[status]}`} data-testid="stock-badge">
      {label}
    </span>
  );
}
