import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Filters } from "@/components/catalog/Filters";
import { Pagination } from "@/components/catalog/Pagination";
import { ProductGrid } from "@/components/catalog/ProductCard";
import { SortSelect } from "@/components/catalog/SortSelect";
import { JsonLd } from "@/components/JsonLd";
import { getCategories, getProducts } from "@/lib/erp";
import { t } from "@/lib/i18n";
import { decodeSlug, hasActiveFilters, parseProductQuery } from "@/lib/search-params";
import { breadcrumbJsonLd } from "@/lib/seo/jsonld";

export const revalidate = 300;

export async function generateStaticParams() {
  const res = await getCategories();
  if (!res.ok) return [];
  const slugs: { slug: string }[] = [];
  const walk = (cats: typeof res.data.categories) =>
    cats.forEach((c) => {
      slugs.push({ slug: c.slug });
      walk(c.children);
    });
  walk(res.data.categories);
  return slugs;
}

export async function generateMetadata({ params }: PageProps<"/c/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const res = await getProducts({ category: decodeSlug(slug), page_size: 1 });
  if (!res.ok || !res.data.category) return { title: t("category.not_found") };
  const c = res.data.category;
  return {
    title: c.title,
    description: c.description || t("brand.description"),
    // filtered/sorted variants of a category page point to the clean URL
    alternates: { canonical: `/c/${encodeURIComponent(c.slug)}` },
    openGraph: { title: c.title, description: c.description || t("brand.description") },
  };
}

export default async function CategoryPage({ params, searchParams }: PageProps<"/c/[slug]">) {
  const { slug } = await params;
  const sp = await searchParams;
  const category = decodeSlug(slug);
  const query = parseProductQuery(sp);
  const res = await getProducts({ ...query, category });
  if (!res.ok) {
    if (res.status === 404 || res.error.code === "category_not_found") notFound();
    throw new Error(res.error.code);
  }
  const { products, pagination, facets, currency } = res.data;
  const info = res.data.category!;
  const urlParams = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) (Array.isArray(v) ? v : v ? [v] : []).forEach((x) => urlParams.append(k, x));

  return (
    <div className="container-page py-6">
      <Breadcrumbs items={info.breadcrumbs.slice(0, -1)} current={info.title} />
      <JsonLd data={breadcrumbJsonLd(info.breadcrumbs)} />
      <h1 className="mt-3 font-heading text-3xl font-bold md:text-4xl">{info.title}</h1>
      {info.description && <p className="mt-2 max-w-2xl text-muted">{info.description}</p>}

      {info.children.length > 0 && (
        <nav aria-label={t("category.subcategories")} className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {info.children.map((c) => (
            <Link key={c.slug} href={`/c/${c.slug}`} className="shrink-0 rounded-pill border border-primary-200 bg-surface px-4 py-2 text-sm hover:bg-primary-50">
              {c.title}
            </Link>
          ))}
        </nav>
      )}

      <div className="mt-6 grid gap-8 lg:grid-cols-[16rem_1fr]">
        <Suspense>
          <Filters facets={facets} showAge={Boolean(info.has_age_filter)} currencySymbol={t("common.currency")} />
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
            <div className="rounded-card bg-surface p-10 text-center">
              <p className="text-muted">{t("category.empty")}</p>
              {hasActiveFilters(query) && (
                <Link href={`/c/${info.slug}`} className="btn btn-outline mt-4">
                  {t("category.clear_filters")}
                </Link>
              )}
            </div>
          )}
          <Pagination pagination={pagination} basePath={`/c/${info.slug}`} params={urlParams} />
        </div>
      </div>
    </div>
  );
}
