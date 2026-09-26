/**
 * Sample catalog used when ERP_MOCK=1 (local development and e2e tests without ERPNext).
 * Product names are sample data, not UI text, so they live here rather than in messages/ar.json.
 */

export type MockGroup = {
  name: string;
  slug: string;
  title: string;
  parent: string | null;
  image: string;
  has_age_filter?: number;
  size_guide?: string;
};

export type MockVariant = {
  code: string;
  size: string | null;
  color: string | null;
  price: number;
  /** Price-list price before a Pricing Rule discount; omit when the item is not on sale. */
  list_price?: number;
  stock: number;
};

export type MockProduct = {
  code: string;
  slug: string;
  name: string;
  group: string;
  description: string;
  images: string[];
  featured?: number;
  age_range?: string;
  created: string;
  price?: number;
  list_price?: number;
  stock?: number;
  variants?: MockVariant[];
};

export const MOCK_COLORS: Record<string, string> = {
  "وردي": "#D8A7B1",
  "بيج": "#E8D9C4",
  "أسود": "#2E2A2B",
  "أبيض": "#FAFAFA",
  "ذهبي": "#CFA96B",
  "أزرق": "#8FB3D9",
};

export const MOCK_SIZES = ["2-3", "4-5", "6-7", "S", "M", "L", "XL"];

export const MOCK_AGE_RANGES = [
  { name: "2-3 سنوات", label: "2-3 سنوات" },
  { name: "4-6 سنوات", label: "4-6 سنوات" },
  { name: "7-10 سنوات", label: "7-10 سنوات" },
];

export const MOCK_GROUPS: MockGroup[] = [
  { name: "Accessories", slug: "accessories", title: "إكسسوارات", parent: null, image: "/mock/accessories.svg" },
  { name: "Bags", slug: "bags", title: "حقائب", parent: "Accessories", image: "/mock/bag.svg" },
  { name: "Jewelry", slug: "jewelry", title: "مجوهرات وأساور", parent: "Accessories", image: "/mock/jewelry.svg" },
  { name: "Gifts", slug: "gifts", title: "هدايا", parent: null, image: "/mock/gift.svg" },
  { name: "Women", slug: "women", title: "ملابس نسائية", parent: null, image: "/mock/dress.svg", size_guide: "women" },
  { name: "Dresses", slug: "dresses", title: "فساتين", parent: "Women", image: "/mock/dress.svg", size_guide: "women" },
  { name: "Abayas", slug: "abayas", title: "عبايات", parent: "Women", image: "/mock/abaya.svg", size_guide: "women" },
  { name: "Kids", slug: "kids", title: "ملابس أطفال", parent: null, image: "/mock/kids.svg", has_age_filter: 1, size_guide: "kids" },
];

export const MOCK_SIZE_GUIDES = {
  women: {
    title: "مقاسات النساء",
    notes: "القياسات بالسنتيمتر وتقريبية.",
    columns: ["size", "chest", "waist", "hips", "length"],
    rows: [
      { size: "S", chest: "86-90", waist: "68-72", hips: "92-96", length: "140" },
      { size: "M", chest: "90-94", waist: "72-76", hips: "96-100", length: "142" },
      { size: "L", chest: "94-100", waist: "76-82", hips: "100-106", length: "144" },
      { size: "XL", chest: "100-106", waist: "82-88", hips: "106-112", length: "146" },
    ],
  },
  kids: {
    title: "مقاسات الأطفال",
    notes: null,
    columns: ["size", "age_label", "height", "chest"],
    rows: [
      { size: "2-3", age_label: "2-3 سنوات", height: "92-98", chest: "53" },
      { size: "4-5", age_label: "4-5 سنوات", height: "104-110", chest: "57" },
      { size: "6-7", age_label: "6-7 سنوات", height: "116-122", chest: "61" },
    ],
  },
};

function variants(prefix: string, sizes: string[], colors: string[], price: number, stock: (i: number) => number) {
  const out: MockVariant[] = [];
  let i = 0;
  for (const size of sizes) {
    for (const color of colors) {
      out.push({ code: `${prefix}-${size}-${Object.keys(MOCK_COLORS).indexOf(color)}`, size, color, price, stock: stock(i++) });
    }
  }
  return out;
}

export const MOCK_PRODUCTS: MockProduct[] = [
  {
    code: "DRESS-001",
    slug: "فستان-سهرة-مطرز",
    name: "فستان سهرة مطرز",
    group: "Dresses",
    description: "<p>فستان سهرة بقصة انسيابية وتطريز يدوي ناعم عند الصدر. قماش شيفون مبطن.</p>",
    images: ["/mock/dress.svg", "/mock/dress-2.svg"],
    featured: 1,
    created: "2026-09-20 10:00:00",
    variants: [
      ...variants("DRESS-001", ["S", "M", "L"], ["وردي", "بيج"], 250, (i) => (i === 1 ? 0 : i === 2 ? 2 : 6)),
      { code: "DRESS-001-XL-1", size: "XL", color: "بيج", price: 280, stock: 3 },
    ],
  },
  {
    code: "ABAYA-001",
    slug: "عباية-كريب-كلاسيك",
    name: "عباية كريب كلاسيك",
    group: "Abayas",
    description: "<p>عباية كريب عملية بأكمام واسعة، مناسبة للاستخدام اليومي.</p>",
    images: ["/mock/abaya.svg"],
    created: "2026-09-18 09:00:00",
    variants: variants("ABAYA-001", ["M", "L", "XL"], ["أسود", "بيج"], 180, () => 5),
  },
  {
    code: "BAG-001",
    slug: "حقيبة-يد-جلد-ناعم",
    name: "حقيبة يد جلد ناعم",
    group: "Bags",
    description: "<p>حقيبة يد أنيقة بحزام قابل للفصل وجيوب داخلية.</p>",
    images: ["/mock/bag.svg"],
    featured: 1,
    created: "2026-09-22 12:00:00",
    variants: variants("BAG-001", [], [], 0, () => 0).concat([
      { code: "BAG-001-0", size: null, color: "وردي", price: 108, list_price: 135, stock: 4 },
      { code: "BAG-001-4", size: null, color: "ذهبي", price: 116, list_price: 145, stock: 2 },
    ]),
  },
  {
    code: "BRACELET-001",
    slug: "إسورة-ذهبية-بحرف",
    name: "إسورة ذهبية بحرف",
    group: "Jewelry",
    description: "<p>إسورة مطلية بالذهب مع حرف من اختيارك. هدية مثالية.</p>",
    images: ["/mock/jewelry.svg"],
    featured: 1,
    created: "2026-09-21 12:00:00",
    price: 65,
    stock: 20,
  },
  {
    code: "GIFT-001",
    slug: "صندوق-هدايا-لمسة",
    name: "صندوق هدايا لمسة",
    group: "Gifts",
    description: "<p>صندوق هدايا فاخر يحتوي على شمعة معطرة ووشاح حريري وبطاقة.</p>",
    images: ["/mock/gift.svg"],
    featured: 1,
    created: "2026-09-23 12:00:00",
    price: 120,
    stock: 8,
  },
  {
    code: "MUG-001",
    slug: "كوب-هدية-بالاسم",
    name: "كوب هدية بالاسم",
    group: "Gifts",
    description: "<p>كوب سيراميك بطباعة الاسم.</p>",
    images: ["/mock/gift.svg"],
    created: "2026-09-10 12:00:00",
    price: 40,
    stock: 0,
  },
  {
    code: "KIDS-001",
    slug: "طقم-أطفال-قطني",
    name: "طقم أطفال قطني",
    group: "Kids",
    description: "<p>طقم قطني مريح من قطعتين للأطفال.</p>",
    images: ["/mock/kids.svg"],
    featured: 1,
    age_range: "4-6 سنوات",
    created: "2026-09-19 12:00:00",
    variants: variants("KIDS-001", ["4-5", "6-7"], ["أزرق", "وردي"], 75, (i) => (i === 0 ? 1 : 5)),
  },
  {
    code: "KIDS-002",
    slug: "فستان-بناتي-بالورود",
    name: "فستان بناتي بالورود",
    group: "Kids",
    description: "<p>فستان بناتي بطبعة ورود وحزام ساتان.</p>",
    images: ["/mock/kids.svg"],
    age_range: "2-3 سنوات",
    created: "2026-09-17 12:00:00",
    variants: variants("KIDS-002", ["2-3"], ["وردي", "أبيض"], 90, () => 4),
  },
];

export const MOCK_ZONES = [
  { zone: "طرابلس-حي الأندلس", city: "طرابلس", area: "حي الأندلس", fee: 15, est_days_min: 1, est_days_max: 2 },
  { zone: "طرابلس-سوق الجمعة", city: "طرابلس", area: "سوق الجمعة", fee: 15, est_days_min: 1, est_days_max: 2 },
  { zone: "طرابلس-جنزور", city: "طرابلس", area: "جنزور", fee: 20, est_days_min: 1, est_days_max: 3 },
  { zone: "بنغازي-الكيش", city: "بنغازي", area: "الكيش", fee: 35, est_days_min: 2, est_days_max: 4 },
  { zone: "مصراتة-المركز", city: "مصراتة", area: "المركز", fee: 30, est_days_min: 2, est_days_max: 3 },
];

export const MOCK_GIFT_WRAP_FEE = 10;
