import type { ProductQuery } from "./erp/types";

export type RawSearchParams = Record<string, string | string[] | undefined>;

const list = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []).filter(Boolean).slice(0, 20);
const num = (v: string | string[] | undefined) => {
  const n = Number(Array.isArray(v) ? v[0] : v);
  return Number.isFinite(n) && n > 0 ? n : undefined;
};
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;

export const SORTS = ["featured", "newest", "price_asc", "price_desc"] as const;

/** URL (?size=S&color=..&age=..&min=..&max=..&stock=1&sort=..&page=..) -> API query */
export function parseProductQuery(sp: RawSearchParams): ProductQuery {
  const sort = one(sp.sort);
  return {
    sizes: list(sp.size),
    colors: list(sp.color),
    age_ranges: list(sp.age),
    min_price: num(sp.min),
    max_price: num(sp.max),
    in_stock: one(sp.stock) === "1",
    sort: sort && (SORTS as readonly string[]).includes(sort) ? sort : undefined,
    page: num(sp.page) ?? 1,
    page_size: 24,
  };
}

export function hasActiveFilters(q: ProductQuery) {
  return Boolean(q.sizes?.length || q.colors?.length || q.age_ranges?.length || q.min_price || q.max_price || q.in_stock);
}

/** Route params may arrive percent-encoded (Arabic slugs); decode safely. */
export function decodeSlug(slug: string): string {
  try {
    return decodeURIComponent(slug);
  } catch {
    return slug;
  }
}
