import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Filters } from "@/components/catalog/Filters";
import { Pagination } from "@/components/catalog/Pagination";
import { ProductGrid } from "@/components/catalog/ProductCard";
import { SortSelect } from "@/components/catalog/SortSelect";
import { getProducts } from "@/lib/erp";
import { t } from "@/lib/i18n";
import { hasActiveFilters, parseProductQuery } from "@/lib/search-params";

export const revalidate = 300;

export const metadata: Metadata = {
  title: t("offers.title"),
  description: t("offers.description"),
  alternates: { canonical: "/offers" },
  openGraph: { title: t("offers.title"), description: t("offers.description") },
};

/**
 * Everything a Pricing Rule has discounted. `on_sale` is decided by ERPNext (see
 * store_core/services/pricing.py), so a product appears here only while its rule actually applies.
 */
export default async function OffersPage({ searchParams }: PageProps<"/offers">) {
  const sp = await searchParams;
  const query = parseProductQuery(sp);
  const res = await getProducts({ ...query, on_sale: true });
  if (!res.ok) throw new Error(res.error.code);

  const { products, pagination, facets, currency } = res.data;
  const urlParams = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) (Array.isArray(v) ? v : v ? [v] : []).forEach((x) => urlParams.append(k, x));

  return (
    <div className="container-page py-6">
      <h1 className="font-heading text-3xl font-bold md:text-4xl">{t("offers.title")}</h1>
      <p className="mt-2 max-w-2xl text-muted">{t("offers.description")}</p>

      <div className="mt-6 grid gap-8 lg:grid-cols-[16rem_1fr]">
        <Suspense>
          <Filters facets={facets} showAge={false} currencySymbol={t("common.currency")} />
        </Suspense>
        <div>
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="text-sm text-muted">{t("category.products_count", { count: pagination.total })}</p>
            <Suspense>
              <SortSelect />
            </Suspense>
          </div>
          {products.length ? (
            <ProductGrid products={products} currency={currency} />
          ) : (
            <div className="rounded-card bg-surface p-10 text-center" data-testid="offers-empty">
              <p className="text-muted">{t("offers.empty")}</p>
              {hasActiveFilters(query) ? (
                <Link href="/offers" className="btn btn-outline mt-4">
                  {t("category.clear_filters")}
                </Link>
              ) : (
                <Link href="/" className="btn btn-primary mt-4">
                  {t("cart.empty_cta")}
                </Link>
              )}
            </div>
          )}
          <Pagination pagination={pagination} basePath="/offers" params={urlParams} />
        </div>
      </div>
    </div>
  );
}
