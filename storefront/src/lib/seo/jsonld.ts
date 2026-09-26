import type { Breadcrumb, ProductDetail } from "../erp/types";
import { mediaUrl, publicEnv } from "../env";
import { t } from "../i18n";

const site = () => publicEnv.siteUrl;

export function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "OnlineStore",
    name: t("brand.name"),
    url: site(),
    description: t("brand.description"),
    areaServed: "LY",
    currenciesAccepted: "LYD",
    paymentAccepted: "Cash",
  };
}

export function breadcrumbJsonLd(items: Breadcrumb[], product?: { name: string; slug: string }) {
  const list = [
    { name: t("nav.home"), url: `${site()}/` },
    ...items.map((b) => ({ name: b.title, url: `${site()}/c/${encodeURIComponent(b.slug)}` })),
    ...(product ? [{ name: product.name, url: `${site()}/p/${encodeURIComponent(product.slug)}` }] : []),
  ];
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: list.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

export function productJsonLd(product: ProductDetail, currency: string) {
  const url = `${site()}/p/${encodeURIComponent(product.slug)}`;
  const images = product.images.map((i) => mediaUrl(i)).filter(Boolean);
  const description = product.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  const availability = (inStock: boolean) =>
    inStock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock";

  if (product.has_variants && product.variants.length) {
    return {
      "@context": "https://schema.org",
      "@type": "ProductGroup",
      name: product.name,
      description,
      url,
      image: images,
      productGroupID: product.code,
      variesBy: [
        ...(product.sizes.length ? ["https://schema.org/size"] : []),
        ...(product.colors.length ? ["https://schema.org/color"] : []),
      ],
      hasVariant: product.variants.map((v) => ({
        "@type": "Product",
        sku: v.code,
        name: [product.name, v.size, v.color].filter(Boolean).join(" - "),
        ...(v.size ? { size: v.size } : {}),
        ...(v.color ? { color: v.color } : {}),
        image: mediaUrl(v.image) ?? images[0],
        offers: {
          "@type": "Offer",
          url,
          price: v.price,
          priceCurrency: currency,
          availability: availability(v.stock.status !== "out"),
          itemCondition: "https://schema.org/NewCondition",
        },
      })),
    };
  }
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    sku: product.code,
    name: product.name,
    description,
    url,
    image: images,
    offers: {
      "@type": "Offer",
      url,
      price: product.min_price,
      priceCurrency: currency,
      availability: availability(product.in_stock),
      itemCondition: "https://schema.org/NewCondition",
    },
  };
}

/** Safe <script type="application/ld+json"> payload (escapes "<"). */
export function jsonLdString(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
