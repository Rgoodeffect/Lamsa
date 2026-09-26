import Link from "next/link";

import type { ProductCard as Card } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

import { Price } from "../Price";
import { ProductImage } from "../ProductImage";

export function ProductCard({ product, currency, priority = false }: { product: Card; currency: string; priority?: boolean }) {
  return (
    <Link
      href={`/p/${encodeURIComponent(product.slug)}`}
      className="group block overflow-hidden rounded-card bg-surface shadow-soft transition hover:-translate-y-0.5"
      data-testid="product-card"
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-primary-50">
        <ProductImage
          src={product.image}
          alt={product.name}
          fill
          priority={priority}
          sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
          className="object-cover transition duration-500 group-hover:scale-105"
        />
        {!product.in_stock && (
          <span className="absolute start-2 top-2 rounded-pill bg-ink/75 px-2.5 py-1 text-xs text-white">
            {t("product.out_of_stock")}
          </span>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        <h3 className="line-clamp-2 text-[0.95rem] font-medium leading-6">{product.name}</h3>
        <Price
          min={product.min_price}
          max={product.max_price}
          listMin={product.list_min_price}
          listMax={product.list_max_price}
          currency={currency}
          className="text-sm"
        />
        {product.colors.length > 1 && (
          <div className="flex gap-1" aria-hidden>
            {product.colors.slice(0, 5).map((c) => (
              <span
                key={c.name}
                className="h-3.5 w-3.5 rounded-full border border-line"
                style={{ background: c.swatch ?? "var(--color-accent-200)" }}
              />
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}

export function ProductGrid({ products, currency }: { products: Card[]; currency: string }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4">
      {products.map((p, i) => (
        <ProductCard key={p.code} product={p} currency={currency} priority={i < 4} />
      ))}
    </div>
  );
}
