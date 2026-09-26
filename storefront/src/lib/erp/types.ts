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

export type SitemapData = { categories: string[]; products: { slug: string; updated: string }[] };

export type PaymentProviderInfo = { code: string; label_key: string; is_online: boolean };

export type StoreConfig = {
  store_name: string;
  currency: string;
  whatsapp: string | null;
  gift_wrap: { enabled: boolean; fee: number; message_max_length: number };
  max_qty_per_line: number;
  payment_providers: PaymentProviderInfo[];
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
};

export type OrderResult = {
  order_no: string;
  status: string;
  currency: string;
  grand_total: number;
  items: { item_code: string; name: string; qty: number; rate: number; amount: number }[];
  zone: PublicZone | null;
  payment_provider: string;
  payment: { status: string; redirect_url?: string | null };
  event_id: string;
  duplicate: boolean;
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
  sort?: string;
  page?: number;
  page_size?: number;
};

export type FeedItem = Record<string, string>;
