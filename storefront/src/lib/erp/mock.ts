// i18n-allow: Arabic letter folding for mock search, not UI text
import "server-only";

import {
  MOCK_AGE_RANGES,
  MOCK_COLORS,
  MOCK_GIFT_WRAP_FEE,
  MOCK_GROUPS,
  MOCK_PRODUCTS,
  MOCK_SIZE_GUIDES,
  MOCK_SIZES,
  MOCK_ZONES,
  type MockProduct,
} from "./mock-data";
import type {
  ApiResult,
  Category,
  CheckoutInput,
  FeedItem,
  ImageSearchResult,
  OrderResult,
  PaymentInstruction,
  PaymentProviderInfo,
  PaymentStatusResult,
  PaymentVerification,
  ProductCard,
  ProductList,
  ProductQuery,
  ProductResponse,
  Quote,
  SearchResponse,
  SitemapData,
  StockLabel,
  StoreConfig,
  TrackResult,
  Zones,
} from "./types";
import { normalizeLibyanPhone } from "../phone";

/**
 * In-memory stand-in for store_core.api.v1 (ERP_MOCK=1). Mirrors the server's validation rules
 * closely enough for UI development and e2e tests. Orders live in process memory.
 */

const CURRENCY = "LYD";
const MAX_QTY = 5;
const ok = <T>(data: T): ApiResult<T> => ({ ok: true, data });
const fail = <T>(code: string, details?: Record<string, string | number>, status = 422): ApiResult<T> => ({
  ok: false,
  error: { code, details },
  status,
});

type Sellable = {
  product: MockProduct;
  code: string;
  size: string | null;
  color: string | null;
  price: number;
  list_price: number;
  stock: number;
};

function sellables(p: MockProduct): Sellable[] {
  if (p.variants?.length) {
    return p.variants.map((v) => ({ product: p, ...v, list_price: v.list_price ?? v.price }));
  }
  return [
    {
      product: p,
      code: p.code,
      size: null,
      color: null,
      price: p.price ?? 0,
      list_price: p.list_price ?? p.price ?? 0,
      stock: p.stock ?? 0,
    },
  ];
}

const heldStock = new Map<string, number>();
const available = (s: Sellable) => s.stock - (heldStock.get(s.code) ?? 0);

function descendants(groupName: string): Set<string> {
  const out = new Set([groupName]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const g of MOCK_GROUPS) {
      if (g.parent && out.has(g.parent) && !out.has(g.name)) {
        out.add(g.name);
        grew = true;
      }
    }
  }
  return out;
}

function card(p: MockProduct): ProductCard {
  const all = sellables(p);
  const prices = all.map((s) => s.price);
  const listPrices = all.map((s) => s.list_price);
  const colors = [...new Set(all.map((s) => s.color).filter(Boolean))] as string[];
  return {
    code: p.code,
    slug: p.slug,
    name: p.name,
    image: p.images[0] ?? null,
    hover_image: p.images[1] ?? null,
    min_price: Math.min(...prices),
    max_price: Math.max(...prices),
    list_min_price: Math.min(...listPrices),
    list_max_price: Math.max(...listPrices),
    on_sale: Math.max(...listPrices) > Math.max(...prices),
    in_stock: all.some((s) => available(s) > 0),
    colors: colors.map((name) => ({ name, swatch: MOCK_COLORS[name] })),
    group_slug: MOCK_GROUPS.find((g) => g.name === p.group)?.slug ?? null,
    featured: p.featured ?? 0,
  };
}

function stockLabel(qty: number): StockLabel {
  if (qty <= 0) return { status: "out", max_qty: 0 };
  if (qty <= 3) return { status: "low", left: qty, max_qty: Math.min(qty, MAX_QTY) };
  return { status: "in", max_qty: Math.min(qty, MAX_QTY) };
}

function breadcrumbs(groupName: string) {
  const trail = [];
  let g = MOCK_GROUPS.find((x) => x.name === groupName);
  while (g) {
    trail.unshift({ slug: g.slug, title: g.title });
    g = MOCK_GROUPS.find((x) => x.name === g!.parent);
  }
  return trail;
}

const normalize = (s: string) =>
  s
    .toLowerCase()
    .replace(/[ؐ-ًؚ-ٰٟـ]/g, "")
    .replace(/[أإآٱ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي");

function sortProducts(list: MockProduct[], sort?: string) {
  const cards = new Map(list.map((p) => [p.code, card(p)]));
  const sorted = [...list].sort((a, b) => b.created.localeCompare(a.created));
  if (sort === "price_asc") return sorted.sort((a, b) => cards.get(a.code)!.min_price - cards.get(b.code)!.min_price);
  if (sort === "price_desc") return sorted.sort((a, b) => cards.get(b.code)!.max_price - cards.get(a.code)!.max_price);
  if (sort === "newest") return sorted;
  return sorted.sort(
    (a, b) =>
      Number(!a.featured) - Number(!b.featured) ||
      Number(!cards.get(a.code)!.in_stock) - Number(!cards.get(b.code)!.in_stock),
  );
}

function paginate<T>(items: T[], page = 1, pageSize = 24) {
  const size = Math.max(1, Math.min(pageSize, 48));
  const p = Math.max(1, page);
  return {
    items: items.slice((p - 1) * size, p * size),
    pagination: { page: p, page_size: size, total: items.length, pages: Math.ceil(items.length / size) },
  };
}

/**
 * Mock payment providers. Cash is always offered; ERP_MOCK_ONLINE_PAYMENT=1 also offers the card
 * provider, so the Lightbox path can be exercised without ERPNext or a merchant account. Its
 * parameters are obviously fake — the real ones are signed by ERPNext with the merchant secret.
 */
const MOCK_ONLINE_PAYMENT = process.env.ERP_MOCK_ONLINE_PAYMENT === "1";
const MOCK_PAYMENT_PROVIDERS: PaymentProviderInfo[] = [
  { code: "cod", label_key: "payment.cod", is_online: false },
  ...(MOCK_ONLINE_PAYMENT ? [{ code: "moamalat", label_key: "payment.moamalat", is_online: true }] : []),
];

function mockPaymentInstruction(provider: string, orderNo: string, total: number): PaymentInstruction {
  if (provider !== "moamalat") return { status: "pending" };
  return {
    status: "lightbox",
    reference: orderNo,
    amount: total,
    extra: {
      script_url: "/mock/lightbox.js",
      environment: "mock",
      params: {
        MID: "MOCK-MID",
        TID: "MOCK-TID",
        AmountTrxn: Math.round(total * 1000),
        MerchantReference: orderNo,
        TrxDateTime: "202601010000",
        SecureHash: "MOCK",
      },
    },
  };
}

/**
 * Mock coupons, mirroring what store_core/services/coupons.py does with ERPNext Coupon Codes:
 * single use, a percentage of the goods only (never delivery or gift wrap), with an expiry.
 * MOCK_COUPON is always available so the flow can be exercised; earned ones are added on delivery.
 */
type MockCoupon = { code: string; percent: number; used: boolean; valid_upto: string };
const coupons = new Map<string, MockCoupon>([
  ["LAMSADEMO10", { code: "LAMSADEMO10", percent: 10, used: false, valid_upto: "2099-12-31" }],
]);

function resolveCoupon(raw: string | undefined): MockCoupon | { error: string } | null {
  const code = (raw ?? "").trim().toUpperCase();
  if (!code) return null;
  const coupon = coupons.get(code);
  if (!coupon) return { error: "invalid_coupon" };
  if (coupon.used) return { error: "coupon_used" };
  if (coupon.valid_upto < new Date().toISOString().slice(0, 10)) return { error: "coupon_expired" };
  return coupon;
}

export const mockApi = {
  async getCategories(): Promise<ApiResult<{ currency: string; categories: Category[] }>> {
    const node = (g: (typeof MOCK_GROUPS)[number]): Category => ({
      slug: g.slug,
      title: g.title,
      image: g.image,
      description: null,
      has_age_filter: g.has_age_filter ?? 0,
      product_count: MOCK_PRODUCTS.filter((p) => descendants(g.name).has(p.group)).length,
      children: MOCK_GROUPS.filter((c) => c.parent === g.name).map(node),
    });
    return ok({ currency: CURRENCY, categories: MOCK_GROUPS.filter((g) => !g.parent).map(node) });
  },

  async getProducts(q: ProductQuery): Promise<ApiResult<ProductList>> {
    let list = MOCK_PRODUCTS;
    const group = q.category ? MOCK_GROUPS.find((g) => g.slug === q.category) : null;
    if (q.category && !group) return fail("category_not_found", undefined, 404);
    if (group) {
      const allowed = descendants(group.name);
      list = list.filter((p) => allowed.has(p.group));
    }
    if (q.on_sale) list = list.filter((p) => card(p).on_sale);
    const scoped = list;
    if (q.featured) list = list.filter((p) => p.featured);
    if (q.age_ranges?.length) list = list.filter((p) => p.age_range && q.age_ranges!.includes(p.age_range));
    if (q.sizes?.length || q.colors?.length || q.in_stock) {
      list = list.filter((p) =>
        sellables(p).some(
          (s) =>
            (!q.sizes?.length || (s.size && q.sizes.includes(s.size))) &&
            (!q.colors?.length || (s.color && q.colors.includes(s.color))) &&
            (!q.in_stock || available(s) > 0),
        ),
      );
    }
    if (q.min_price !== undefined) list = list.filter((p) => card(p).max_price >= q.min_price!);
    if (q.max_price !== undefined) list = list.filter((p) => card(p).min_price <= q.max_price!);

    const { items, pagination } = paginate(sortProducts(list, q.sort), q.page, q.page_size);
    const all = scoped.flatMap(sellables);
    const prices = scoped.map(card).flatMap((c) => [c.min_price, c.max_price]);
    return ok({
      currency: CURRENCY,
      category: group
        ? {
            slug: group.slug,
            title: group.title,
            image: group.image,
            description: null,
            has_age_filter: group.has_age_filter ?? 0,
            breadcrumbs: breadcrumbs(group.name),
            children: MOCK_GROUPS.filter((g) => g.parent === group.name).map((g) => ({
              slug: g.slug,
              title: g.title,
              image: g.image,
            })),
          }
        : null,
      products: items.map(card),
      pagination,
      facets: {
        sizes: MOCK_SIZES.filter((s) => all.some((x) => x.size === s)),
        colors: [...new Set(all.map((x) => x.color).filter(Boolean))].map((name) => ({
          name: name!,
          swatch: MOCK_COLORS[name!],
        })),
        age_ranges: MOCK_AGE_RANGES.filter((a) => scoped.some((p) => p.age_range === a.name)),
        price: { min: prices.length ? Math.min(...prices) : 0, max: prices.length ? Math.max(...prices) : 0 },
      },
    });
  },

  async getProduct(slug: string): Promise<ApiResult<ProductResponse>> {
    const p = MOCK_PRODUCTS.find((x) => x.slug === slug);
    if (!p) return fail("product_not_found", undefined, 404);
    const c = card(p);
    const group = MOCK_GROUPS.find((g) => g.name === p.group);
    let guideKey = group?.size_guide;
    if (!guideKey && group?.parent) guideKey = MOCK_GROUPS.find((g) => g.name === group.parent)?.size_guide;
    const hasVariants = Boolean(p.variants?.length);
    return ok({
      currency: CURRENCY,
      product: {
        code: p.code,
        slug: p.slug,
        name: p.name,
        description: p.description,
        images: p.images,
        min_price: c.min_price,
        max_price: c.max_price,
        list_min_price: c.list_min_price,
        list_max_price: c.list_max_price,
        on_sale: c.on_sale,
        in_stock: c.in_stock,
        has_variants: hasVariants ? 1 : 0,
        stock: hasVariants ? null : stockLabel(available(sellables(p)[0])),
        sizes: MOCK_SIZES.filter((s) => p.variants?.some((v) => v.size === s)),
        colors: c.colors,
        variants: (p.variants ?? []).map((v) => ({
          code: v.code,
          size: v.size,
          color: v.color,
          attributes: Object.fromEntries(
            [
              ["Size", v.size],
              ["Color", v.color],
            ].filter(([, val]) => val),
          ),
          price: v.price,
          list_price: v.list_price ?? v.price,
          image: null,
          stock: stockLabel(available({ product: p, ...v, list_price: v.list_price ?? v.price })),
        })),
        age_range: p.age_range ?? null,
        group_slug: group?.slug ?? null,
        breadcrumbs: breadcrumbs(p.group),
        size_guide: guideKey ? MOCK_SIZE_GUIDES[guideKey as keyof typeof MOCK_SIZE_GUIDES] : null,
      },
      related: MOCK_PRODUCTS.filter((x) => x.group === p.group && x.code !== p.code).map(card),
    });
  },

  async search(query: string, page = 1): Promise<ApiResult<SearchResponse>> {
    const tokens = normalize(query.trim()).split(/\s+/).filter(Boolean);
    const list = tokens.length
      ? MOCK_PRODUCTS.filter((p) => {
          const text = normalize(`${p.name} ${p.code} ${MOCK_GROUPS.find((g) => g.name === p.group)?.title ?? ""}`);
          return tokens.every((t) => text.includes(t));
        })
      : [];
    const { items, pagination } = paginate(list, page);
    return ok({ currency: CURRENCY, query, products: items.map(card), pagination });
  },

  async getSitemap(): Promise<ApiResult<SitemapData>> {
    return ok({
      categories: MOCK_GROUPS.map((g) => g.slug),
      products: MOCK_PRODUCTS.map((p) => ({ slug: p.slug, updated: p.created })),
    });
  },

  async getConfig(): Promise<ApiResult<StoreConfig>> {
    return ok({
      store_name: "Lamsa",
      currency: CURRENCY,
      whatsapp: "218912345678",
      gift_wrap: { enabled: true, fee: MOCK_GIFT_WRAP_FEE, message_max_length: 250 },
      max_qty_per_line: MAX_QTY,
      payment_providers: MOCK_PAYMENT_PROVIDERS,
      image_search: true,
    });
  },

  async getZones(): Promise<ApiResult<Zones>> {
    const cities = [...new Set(MOCK_ZONES.map((z) => z.city))];
    return ok({
      cities: cities.map((city) => ({
        city,
        areas: MOCK_ZONES.filter((z) => z.city === city).map(({ zone, area, fee, est_days_min, est_days_max }) => ({
          zone,
          area,
          fee,
          est_days_min,
          est_days_max,
        })),
      })),
    });
  },

  async quote(body: {
    items: { item_code: string; qty: number }[];
    zone?: string;
    gift_wrap?: boolean;
    coupon_code?: string;
  }): Promise<ApiResult<Quote>> {
    const lines = validateCart(body.items);
    if ("error" in lines) return fail(lines.error, lines.details);
    const zone = body.zone ? MOCK_ZONES.find((z) => z.zone === body.zone) : null;
    if (body.zone && !zone) return fail("invalid_zone");
    const resolved = resolveCoupon(body.coupon_code);
    // as in store_core.services.orders.quote: a bad coupon is reported, never fatal to the quote
    const couponError = resolved && "error" in resolved ? resolved.error : null;
    const coupon = resolved && "error" in resolved ? null : resolved;
    const items = lines.map(({ s, qty }) => ({
      item_code: s.code,
      name: s.product.name,
      slug: s.product.slug,
      image: s.product.images[0] ?? null,
      attributes: Object.fromEntries(
        [
          ["Size", s.size],
          ["Color", s.color],
        ].filter(([, v]) => v),
      ) as Record<string, string>,
      qty,
      price_list_rate: s.price,
      rate: s.price,
      amount: s.price * qty,
    }));
    const subtotal = items.reduce((sum, i) => sum + i.amount, 0);
    const giftWrapFee = body.gift_wrap ? MOCK_GIFT_WRAP_FEE : 0;
    const deliveryFee = zone?.fee ?? 0;
    // the goods only, as in store_core/services/coupons.py
    const discount = coupon ? Math.round(subtotal * (coupon.percent / 100) * 100) / 100 : 0;
    return ok({
      currency: CURRENCY,
      items,
      subtotal,
      gift_wrap_fee: giftWrapFee,
      delivery_fee: deliveryFee,
      discount,
      taxes: 0,
      grand_total: subtotal + giftWrapFee + deliveryFee - discount,
      zone: zone
        ? { name: zone.zone, city: zone.city, area: zone.area, fee: zone.fee, est_days_min: zone.est_days_min, est_days_max: zone.est_days_max }
        : null,
      coupon: coupon
        ? { code: coupon.code, percent: coupon.percent, discount, valid_upto: coupon.valid_upto }
        : null,
      coupon_error: couponError,
    });
  },

  async placeOrder(input: CheckoutInput): Promise<ApiResult<OrderResult>> {
    const existing = [...orders.values()].find((o) => o.result.event_id === input.event_id);
    if (existing) return ok({ ...existing.result, duplicate: true });
    const name = (input.full_name || "").trim();
    if (name.length < 2) return fail("invalid_name");
    const phone = normalizeLibyanPhone(input.phone);
    if (!phone) return fail("invalid_phone");
    if (!/^[A-Za-z0-9_-]{8,64}$/.test(input.event_id || "")) return fail("invalid_event_id");
    if (!input.zone) return fail("invalid_zone");
    const provider = input.payment_provider || "cod";
    if (!MOCK_PAYMENT_PROVIDERS.some((p) => p.code === provider)) return fail("payment_unavailable");
    if (input.gift_wrap && (input.gift_message || "").length > 250) return fail("gift_message_too_long");
    const q = await mockApi.quote({
      items: input.items,
      zone: input.zone,
      gift_wrap: input.gift_wrap,
      coupon_code: input.coupon_code,
    });
    if (!q.ok) return q;
    // Checkout is strict where the quote is lenient, as store_core.services.orders.place_order is:
    // the customer must not lose a discount they were counting on without being told.
    if (q.data.coupon_error) return fail(q.data.coupon_error);
    // single use, as ERPNext's on_submit counter enforces on the real backend
    if (q.data.coupon) coupons.get(q.data.coupon.code)!.used = true;
    for (const line of q.data.items) heldStock.set(line.item_code, (heldStock.get(line.item_code) ?? 0) + line.qty);
    const orderNo = `L-${String(10001 + orders.size)}`;
    const result: OrderResult = {
      order_no: orderNo,
      status: "New",
      currency: CURRENCY,
      grand_total: q.data.grand_total,
      items: q.data.items.map((i) => ({ item_code: i.item_code, name: i.name, qty: i.qty, rate: i.rate, amount: i.amount })),
      zone: q.data.zone,
      payment_provider: provider,
      payment: mockPaymentInstruction(provider, orderNo, q.data.grand_total),
      payment_status: "Unpaid",
      discount: q.data.discount,
      coupon_code: q.data.coupon?.code ?? null,
      event_id: input.event_id,
      duplicate: false,
    };
    orders.set(orderNo, { phone, result, placedOn: new Date().toISOString(), giftWrap: Boolean(input.gift_wrap) });
    return ok(result);
  },

  async trackOrder(orderNo: string, phoneRaw: string): Promise<ApiResult<TrackResult>> {
    const order = orders.get((orderNo || "").trim().toUpperCase());
    const phone = normalizeLibyanPhone(phoneRaw);
    if (!order || !phone || order.phone !== phone) return fail("order_not_found", undefined, 404);
    const rest: Partial<OrderResult> = { ...order.result };
    delete rest.event_id;
    delete rest.payment;
    return ok({
      ...(rest as Omit<OrderResult, "event_id" | "payment">),
      steps: ["New", "Confirmed", "Out for Delivery", "Delivered"],
      step_index: 0,
      placed_on: order.placedOn,
      updated_on: order.placedOn,
      gift_wrap: order.giftWrap ? 1 : 0,
    });
  },

  /** Mock gateway: any payload naming a known order is treated as a successful payment. */
  async verifyMoamalatPayment(payload: Record<string, unknown>): Promise<ApiResult<PaymentVerification>> {
    const orderNo = String(payload?.MerchantReference ?? "").trim().toUpperCase();
    const order = orders.get(orderNo);
    if (!order) return fail("order_not_found", undefined, 404);
    if (payload?.ErrorMessage) {
      order.result.payment_status = "Failed";
      return ok({ status: "failed", provider: "moamalat", order_no: orderNo, message: "payment_failed" });
    }
    order.result.payment_status = "Paid";
    order.result.payment = { status: "paid" };
    return ok({ status: "paid", provider: "moamalat", order_no: orderNo, message: null });
  },

  async getPaymentStatus(orderNo: string, eventId: string): Promise<ApiResult<PaymentStatusResult>> {
    const order = orders.get((orderNo || "").trim().toUpperCase());
    if (!order || order.result.event_id !== eventId) return fail("order_not_found", undefined, 404);
    return ok({
      order_no: order.result.order_no,
      payment_status: order.result.payment_status ?? "Unpaid",
      payment_provider: order.result.payment_provider,
      status: order.result.status,
    });
  },

  /**
   * Mock image search. There is no model here, so it cannot judge what a photo looks like: it returns
   * the featured products so the upload, loading and result states can be built and tested. The real
   * ranking is store_core/services/vectors.py, which has its own unit tests.
   */
  async searchByImage(imageBase64: string, limit: number): Promise<ApiResult<ImageSearchResult>> {
    if (!imageBase64) return fail("image_required");
    // roughly the byte length of the base64 payload, to exercise the same limit as the backend
    if (imageBase64.length * 0.75 > 8 * 1024 * 1024) return fail("image_too_large");
    const cards = MOCK_PRODUCTS.map(card).filter((c) => c.in_stock).slice(0, limit);
    return ok({
      products: cards.map((c, i) => ({ ...c, score: Math.round((0.95 - i * 0.03) * 10000) / 10000 })),
      matched: cards.length,
      indexed: MOCK_PRODUCTS.length,
    });
  },

  async getMetaFeed(): Promise<ApiResult<{ currency: string; items: FeedItem[] }>> {
    const items: FeedItem[] = [];
    for (const p of MOCK_PRODUCTS) {
      for (const s of sellables(p)) {
        items.push({
          id: s.code,
          item_group_id: p.code,
          title: p.name,
          description: p.description.replace(/<[^>]+>/g, ""),
          availability: available(s) > 0 ? "in stock" : "out of stock",
          condition: "new",
          // as in store_core.services.feed: `price` is the price-list rate, `sale_price` the discount
          price: `${s.list_price.toFixed(2)} ${CURRENCY}`,
          sale_price: s.price < s.list_price ? `${s.price.toFixed(2)} ${CURRENCY}` : "",
          slug: p.slug,
          image_link: p.images[0],
          additional_image_link: p.images.slice(1).join(","),
          brand: "Lamsa",
          size: s.size ?? "",
          color: s.color ?? "",
          product_type: breadcrumbs(p.group).map((b) => b.title).join(" > "),
          age_group: p.group === "Kids" ? "kids" : "adult",
          gender: p.group === "Kids" ? "unisex" : "",
        });
      }
    }
    return ok({ currency: CURRENCY, items });
  },
};

const orders = new Map<string, { phone: string; result: OrderResult; placedOn: string; giftWrap: boolean }>();

function validateCart(
  items: { item_code: string; qty: number }[] | undefined,
): { s: Sellable; qty: number }[] | { error: string; details?: Record<string, string | number> } {
  if (!Array.isArray(items) || !items.length) return { error: "cart_empty" };
  const merged = new Map<string, number>();
  for (const row of items) {
    const qty = Math.floor(Number(row?.qty));
    if (!row?.item_code || !(qty >= 1)) return { error: "invalid_item" };
    merged.set(row.item_code, (merged.get(row.item_code) ?? 0) + qty);
  }
  const lines = [];
  for (const [code, qty] of merged) {
    const s = MOCK_PRODUCTS.flatMap(sellables).find((x) => x.code === code && (x.product.variants?.length ? x.code !== x.product.code : true));
    if (!s) return { error: "item_unavailable", details: { item_code: code } };
    if (qty > MAX_QTY) return { error: "qty_limit", details: { item_code: code, max_qty: MAX_QTY } };
    if (qty > available(s)) return { error: "out_of_stock", details: { item_code: code, available: Math.max(available(s), 0) } };
    lines.push({ s, qty });
  }
  return lines;
}
