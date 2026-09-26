import "server-only";

import { CACHE_TAGS, callErp } from "./client";
import { mockApi } from "./mock";
import type {
  ApiResult,
  Category,
  CheckoutInput,
  FeedItem,
  OrderResult,
  ProductList,
  ProductQuery,
  ProductResponse,
  Quote,
  SearchResponse,
  SitemapData,
  StoreConfig,
  TrackResult,
  Zones,
} from "./types";

export { CACHE_TAGS };
export const isMock = process.env.ERP_MOCK === "1";

/** Catalog pages revalidate every 5 minutes, and immediately when ERPNext calls /api/revalidate. */
const CATALOG_TTL = 300;

export function getCategories(): Promise<ApiResult<{ currency: string; categories: Category[] }>> {
  if (isMock) return mockApi.getCategories();
  return callErp("catalog.get_categories", { revalidate: CATALOG_TTL, tags: [CACHE_TAGS.catalog] });
}

export function getProducts(query: ProductQuery): Promise<ApiResult<ProductList>> {
  if (isMock) return mockApi.getProducts(query);
  return callErp("catalog.get_products", {
    params: {
      category: query.category,
      sizes: query.sizes,
      colors: query.colors,
      age_ranges: query.age_ranges,
      min_price: query.min_price,
      max_price: query.max_price,
      in_stock: query.in_stock ? 1 : undefined,
      featured: query.featured ? 1 : undefined,
      sort: query.sort,
      page: query.page,
      page_size: query.page_size,
    },
    revalidate: CATALOG_TTL,
    tags: [CACHE_TAGS.catalog, CACHE_TAGS.products],
  });
}

export function getProduct(slug: string): Promise<ApiResult<ProductResponse>> {
  if (isMock) return mockApi.getProduct(slug);
  return callErp("catalog.get_product", {
    params: { slug },
    revalidate: CATALOG_TTL,
    tags: [CACHE_TAGS.catalog, CACHE_TAGS.products],
  });
}

export function searchProducts(q: string, page = 1): Promise<ApiResult<SearchResponse>> {
  if (isMock) return mockApi.search(q, page);
  return callErp("catalog.search", { params: { q, page }, revalidate: 60, tags: [CACHE_TAGS.products] });
}

export function getSitemap(): Promise<ApiResult<SitemapData>> {
  if (isMock) return mockApi.getSitemap();
  return callErp("catalog.get_sitemap", { revalidate: 3600, tags: [CACHE_TAGS.catalog] });
}

export function getStoreConfig(): Promise<ApiResult<StoreConfig>> {
  if (isMock) return mockApi.getConfig();
  return callErp("store.get_config", { revalidate: 600, tags: [CACHE_TAGS.config] });
}

export function getZones(): Promise<ApiResult<Zones>> {
  if (isMock) return mockApi.getZones();
  return callErp("store.get_zones", { revalidate: 600, tags: [CACHE_TAGS.config] });
}

export function quoteCart(
  body: { items: { item_code: string; qty: number }[]; zone?: string; gift_wrap?: boolean },
  clientIp: string,
): Promise<ApiResult<Quote>> {
  if (isMock) return mockApi.quote(body);
  return callErp("cart.quote", { method: "POST", body: { ...body, gift_wrap: body.gift_wrap ? 1 : 0 }, clientIp });
}

export function placeOrder(input: CheckoutInput, clientIp: string): Promise<ApiResult<OrderResult>> {
  if (isMock) return mockApi.placeOrder(input);
  return callErp("checkout.place_order", {
    method: "POST",
    body: { ...input, gift_wrap: input.gift_wrap ? 1 : 0, source: "Storefront" },
    clientIp,
  });
}

export function trackOrder(orderNo: string, phone: string, clientIp: string): Promise<ApiResult<TrackResult>> {
  if (isMock) return mockApi.trackOrder(orderNo, phone);
  return callErp("orders.track_order", { method: "POST", body: { order_no: orderNo, phone }, clientIp });
}

export function getMetaFeed(): Promise<ApiResult<{ currency: string; items: FeedItem[] }>> {
  if (isMock) return mockApi.getMetaFeed();
  return callErp("feeds.meta_catalog", { revalidate: 3600, tags: [CACHE_TAGS.catalog, CACHE_TAGS.products] });
}
