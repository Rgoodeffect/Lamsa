import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { ProductGrid } from "@/components/catalog/ProductCard";
import { JsonLd } from "@/components/JsonLd";
import { ProductView } from "@/components/product/ProductView";
import { mediaUrl, publicEnv } from "@/lib/env";
import { getProduct, getSitemap, getStoreConfig } from "@/lib/erp";
import { t } from "@/lib/i18n";
import { plainText, sanitizeHtml } from "@/lib/sanitize";
import { decodeSlug } from "@/lib/search-params";
import { breadcrumbJsonLd, productJsonLd } from "@/lib/seo/jsonld";

export const revalidate = 300;

/** Pre-render every published product at build; new ones render on first visit (ISR). */
export async function generateStaticParams() {
  const res = await getSitemap();
  return res.ok ? res.data.products.slice(0, 500).map((p) => ({ slug: p.slug })) : [];
}

export async function generateMetadata({ params }: PageProps<"/p/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const res = await getProduct(decodeSlug(slug));
  if (!res.ok) return { title: t("product.not_found") };
  const p = res.data.product;
  const description = p.seo_description || plainText(p.description) || t("brand.description");
  const image = mediaUrl(p.images[0]);
  return {
    title: p.seo_title || p.name,
    description,
    alternates: { canonical: `/p/${encodeURIComponent(p.slug)}` },
    openGraph: {
      type: "website",
      title: p.seo_title || p.name,
      description,
      url: `/p/${encodeURIComponent(p.slug)}`,
      images: image ? [{ url: image, alt: p.name }] : undefined,
    },
    other: {
      "product:price:amount": String(p.min_price),
      "product:price:currency": res.data.currency,
      "product:availability": p.in_stock ? "in stock" : "out of stock",
    },
  };
}

export default async function ProductPage({ params }: PageProps<"/p/[slug]">) {
  const { slug } = await params;
  const [res, config] = await Promise.all([getProduct(decodeSlug(slug)), getStoreConfig()]);
  if (!res.ok) {
    if (res.status === 404 || res.error.code === "product_not_found") notFound();
    throw new Error(res.error.code);
  }
  const { product, related, currency } = res.data;
  const safeProduct = { ...product, description: sanitizeHtml(product.description) };
  const url = `${publicEnv.siteUrl}/p/${encodeURIComponent(product.slug)}`;
  const whatsapp = (config.ok && config.data.whatsapp) || publicEnv.whatsappNumber || null;

  return (
    <div className="container-page py-6">
      <Breadcrumbs items={product.breadcrumbs} current={product.name} />
      <div className="mt-4">
        <ProductView product={safeProduct} currency={currency} whatsapp={whatsapp} productUrl={url} />
      </div>
      {related.length > 0 && (
        <section className="mt-16">
          <h2 className="mb-5 font-heading text-2xl font-bold">{t("product.related")}</h2>
          <ProductGrid products={related} currency={currency} />
        </section>
      )}
      <JsonLd data={productJsonLd(product, currency)} />
      <JsonLd data={breadcrumbJsonLd(product.breadcrumbs, { name: product.name, slug: product.slug })} />
    </div>
  );
}
