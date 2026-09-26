/** Shapes returned by store_core.api.v1 (see store_core/api/v1/*.py). */

export type ApiError = { code: string; details?: Record<string, string | number> };
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError; status?: number };

export type Category = {
  slug: string;
  title: string;
  description?: string | null;
  image?: string | null;
  product_count: number;
  has_age_filter: number;
  children: Category[];
};

export type ColorOption = { name: string; swatch?: string | null };

export type ProductCard = {
  code: string;
  slug: string;
  name: string;
  image: string | null;
  hover_image: string | null;
  min_price: number;
  max_price: number;
  /** Price-list prices before any catalog discount; equal to min/max when nothing is on sale. */
  list_min_price: number;
  list_max_price: number;
  on_sale: boolean;
  in_stock: boolean;
  colors: ColorOption[];
  group_slug: string | null;
  featured: number;
};

export type Facets = {
  sizes: string[];
  colors: ColorOption[];
  age_ranges: { name: string; label: string }[];
  price: { min: number; max: number };
};

export type Pagination = { page: number; page_size: number; total: number; pages: number };

export type Breadcrumb = { slug: string; title: string };

export type CategoryInfo = {
  slug: string;
  title: string;
  description?: string | null;
  image?: string | null;
  has_age_filter: number;
  breadcrumbs: Breadcrumb[];
  children: { slug: string; title: string; image?: string | null }[];
};

export type ProductList = {
  currency: string;
  category: CategoryInfo | null;
  products: ProductCard[];
  pagination: Pagination;
  facets: Facets;
};

export type StockLabel = { status: "in" | "low" | "out"; left?: number; max_qty: number };

export type Variant = {
  code: string;
  size: string | null;
  color: string | null;
  attributes: Record<string, string>;
  price: number;
  /** Price-list price before any catalog discount; equal to `price` when not on sale. */
  list_price: number;
  image: string | null;
  stock: StockLabel;
};

export type SizeGuide = {
  title: string;
  notes?: string | null;
  columns: string[];
  rows: Record<string, string | null>[];
};

export type ProductDetail = {
  code: string;
  slug: string;
  name: string;
  description: string;
  seo_title?: string | null;
  seo_description?: string | null;
  brand?: string | null;
  images: string[];
  min_price: number;
  max_price: number;
  list_min_price: number;
  list_max_price: number;
  on_sale: boolean;
  in_stock: boolean;
  has_variants: number;
  stock: StockLabel | null;
  sizes: string[];
  colors: ColorOption[];
  variants: Variant[];
  age_range?: string | null;
  group_slug: string | null;
  breadcrumbs: Breadcrumb[];
  size_guide: SizeGuide | null;
};

export type ProductResponse = { currency: string; product: ProductDetail; related: ProductCard[] };

export type SearchResponse = {
  currency: string;
  query: string;
  products: ProductCard[];
  pagination: Pagination;
};

/** A product card plus how close its best image was to the uploaded photo. */
export type ImageMatch = ProductCard & { score: number };

export type ImageSearchResult = {
  products: ImageMatch[];
  matched: number;
  /** How many product images are encoded; 0 means the index has not been built yet. */
  indexed: number;
};

export type SitemapData = { categories: string[]; products: { slug: string; updated: string }[] };

export type PaymentProviderInfo = { code: string; label_key: string; is_online: boolean };

export type StoreConfig = {
  store_name: string;
  currency: string;
  whatsapp: string | null;
  gift_wrap: { enabled: boolean; fee: number; message_max_length: number };
  max_qty_per_line: number;
  payment_providers: PaymentProviderInfo[];
  /** False when the model or its runtime is missing, so the control is not offered at all. */
  image_search: boolean;
};

export type ZoneArea = { zone: string; area: string; fee: number; est_days_min: number; est_days_max: number };
export type Zones = { cities: { city: string; areas: ZoneArea[] }[] };

export type CartLineInput = { item_code: string; qty: number };

export type QuoteItem = {
  item_code: string;
  name: string;
  slug: string | null;
  image: string | null;
  attributes: Record<string, string>;
  qty: number;
  price_list_rate: number;
  rate: number;
  amount: number;
};

export type PublicZone = {
  name: string;
  city: string;
  area: string;
  fee: number;
  est_days_min: number;
  est_days_max: number;
};

/** A coupon the server accepted, with what it actually took off this cart. */
export type AppliedCoupon = {
  code: string;
  percent: number;
  discount: number;
  valid_upto: string;
};

export type Quote = {
  currency: string;
  items: QuoteItem[];
  subtotal: number;
  gift_wrap_fee: number;
  delivery_fee: number;
  discount: number;
  taxes: number;
  grand_total: number;
  zone: PublicZone | null;
  coupon: AppliedCoupon | null;
  /** Why the coupon the browser sent was not applied; the totals above exclude it. */
  coupon_error: string | null;
};

export type CheckoutInput = {
  items: CartLineInput[];
  full_name: string;
  phone: string;
  zone: string;
  event_id: string;
  address_notes?: string;
  gift_wrap?: boolean;
  gift_message?: string;
  payment_provider?: string;
  coupon_code?: string;
};

/** Parameters the Moamalat Lightbox widget is opened with (built and signed by ERPNext). */
export type LightboxParams = {
  MID: string;
  TID: string;
  AmountTrxn: number;
  MerchantReference: string;
  TrxDateTime: string;
  SecureHash: string;
};

export type PaymentInstruction = {
  /** "pending" (cash), "redirect" (hosted page), "lightbox" (embedded widget), "paid", "failed" */
  status: string;
  redirect_url?: string | null;
  reference?: string | null;
  amount?: number | null;
  message?: string | null;
  extra?: {
    script_url?: string;
    environment?: string;
    params?: LightboxParams;
  } | null;
};

export type OrderResult = {
  order_no: string;
  status: string;
  currency: string;
  grand_total: number;
  items: { item_code: string; name: string; qty: number; rate: number; amount: number }[];
  zone: PublicZone | null;
  payment_provider: string;
  payment: PaymentInstruction;
  payment_status?: string;
  discount?: number;
  coupon_code?: string | null;
  event_id: string;
  duplicate: boolean;
};

export type PaymentStatusResult = {
  order_no: string;
  payment_status: string;
  payment_provider: string;
  status: string;
};

/** Outcome of a gateway callback, as verified by ERPNext. */
export type PaymentVerification = {
  status: string;
  provider: string;
  order_no?: string | null;
  message?: string | null;
};

export type TrackResult = Omit<OrderResult, "event_id" | "payment"> & {
  steps: string[];
  step_index: number;
  placed_on: string;
  updated_on: string;
  gift_wrap: number;
};

export type ProductQuery = {
  category?: string;
  sizes?: string[];
  colors?: string[];
  age_ranges?: string[];
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  featured?: boolean;
  /** Only products a Pricing Rule has discounted (the offers section). */
  on_sale?: boolean;
  sort?: string;
  page?: number;
  page_size?: number;
};

export type FeedItem = Record<string, string>;
