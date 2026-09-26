import type { Metadata } from "next";
import { Suspense } from "react";

import { Pagination } from "@/components/catalog/Pagination";
import { ProductGrid } from "@/components/catalog/ProductCard";
import { SortSelect } from "@/components/catalog/SortSelect";
import { SearchIcon } from "@/components/Icons";
import { ImageSearch } from "@/components/catalog/ImageSearch";
import { getProducts, getStoreConfig, searchProducts } from "@/lib/erp";
import { t } from "@/lib/i18n";
import { parseProductQuery } from "@/lib/search-params";

export const metadata: Metadata = { title: t("search.title"), robots: { index: false, follow: true } };

export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const sp = await searchParams;
  const q = (Array.isArray(sp.q) ? sp.q[0] : sp.q)?.trim().slice(0, 80) ?? "";
  const query = parseProductQuery(sp);

  // With a query: search. Without: browse all products (used by "view all").
  const [res, config] = await Promise.all([
    q ? searchProducts(q, query.page) : getProducts(query),
    getStoreConfig(),
  ]);
  const data = res.ok ? res.data : null;
  const imageSearch = config.ok && config.data.image_search;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (query.sort) params.set("sort", query.sort);

  return (
    <div className="container-page py-8">
      <form action="/search" role="search" className="mx-auto flex max-w-xl gap-2">
        <input
          name="q"
          defaultValue={q}
          className="field"
          placeholder={t("search.placeholder")}
          aria-label={t("search.placeholder")}
          enterKeyHint="search"
        />
        <button className="btn btn-primary px-4" aria-label={t("search.submit")}>
          <SearchIcon size={20} />
        </button>
      </form>

      {imageSearch ? <ImageSearch currency={data?.currency ?? t("common.currency")} /> : null}

      <div className="mt-8 mb-4 flex items-center justify-between gap-3">
        <h1 className="font-heading text-2xl font-bold">{q ? t("search.results_for", { query: q }) : t("search.title")}</h1>
        {!q && (
          <Suspense>
            <SortSelect />
          </Suspense>
        )}
      </div>

      {data && data.products.length > 0 ? (
        <>
          <ProductGrid products={data.products} currency={data.currency} />
          <Pagination pagination={data.pagination} basePath="/search" params={params} />
        </>
      ) : (
        q && <p className="rounded-card bg-surface p-10 text-center text-muted">{t("search.no_results")}</p>
      )}
    </div>
  );
}
