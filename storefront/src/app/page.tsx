import Link from "next/link";

import { ProductGrid } from "@/components/catalog/ProductCard";
import { CashIcon, ChatIcon, GiftIcon, TruckIcon } from "@/components/Icons";
import { ProductImage } from "@/components/ProductImage";
import { getCategories, getProducts } from "@/lib/erp";
import { t } from "@/lib/i18n";

export const revalidate = 300;

export default async function HomePage() {
  const [categories, featured, newest] = await Promise.all([
    getCategories(),
    getProducts({ featured: true, page_size: 8 }),
    getProducts({ sort: "newest", page_size: 8 }),
  ]);
  const cats = categories.ok ? categories.data.categories : [];
  const currency = featured.ok ? featured.data.currency : "LYD";

  const perks = [
    { icon: CashIcon, title: t("home.perk.cod.title"), text: t("home.perk.cod.text") },
    { icon: TruckIcon, title: t("home.perk.delivery.title"), text: t("home.perk.delivery.text") },
    { icon: GiftIcon, title: t("home.perk.gift.title"), text: t("home.perk.gift.text") },
    { icon: ChatIcon, title: t("home.perk.whatsapp.title"), text: t("home.perk.whatsapp.text") },
  ];

  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-bl from-primary-100 via-cream to-accent-100">
        <div className="container-page grid items-center gap-8 py-12 md:grid-cols-2 md:py-20">
          <div className="space-y-5 text-center md:text-start">
            <h1 className="whitespace-pre-line font-heading text-4xl font-bold text-primary-800 md:text-6xl">
              {t("home.hero.title")}
            </h1>
            <p className="text-lg text-muted">{t("home.hero.subtitle")}</p>
            <Link href={cats[0] ? `/c/${cats[0].slug}` : "/search"} className="btn btn-primary text-lg">
              {t("home.hero.cta")}
            </Link>
          </div>
          <div aria-hidden className="mx-auto hidden aspect-square w-full max-w-md rounded-[40%_60%_55%_45%] bg-primary-200/60 md:block">
            <div className="h-full w-full rounded-[inherit] bg-[radial-gradient(circle_at_30%_30%,var(--color-accent-100),transparent_60%)]" />
          </div>
        </div>
      </section>

      <section className="container-page -mt-6 relative z-10">
        <ul className="grid grid-cols-2 gap-3 rounded-card bg-surface p-4 shadow-soft md:grid-cols-4">
          {perks.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex items-start gap-3">
              <span className="rounded-full bg-accent-100 p-2 text-accent-600">
                <Icon size={20} />
              </span>
              <span>
                <span className="block text-sm font-semibold">{title}</span>
                <span className="block text-xs text-muted">{text}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      {cats.length > 0 && (
        <section className="container-page mt-12">
          <h2 className="mb-5 font-heading text-2xl font-bold md:text-3xl">{t("home.categories")}</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-5">
            {cats.map((c) => (
              <Link
                key={c.slug}
                href={`/c/${c.slug}`}
                className="group relative block aspect-[4/5] overflow-hidden rounded-card bg-primary-100"
              >
                <ProductImage
                  src={c.image}
                  alt={c.title}
                  fill
                  sizes="(min-width: 768px) 25vw, 50vw"
                  className="object-cover transition duration-500 group-hover:scale-105"
                />
                <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-primary-900/70 to-transparent p-4 font-heading text-xl font-bold text-white">
                  {c.title}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {featured.ok && featured.data.products.length > 0 && (
        <section className="container-page mt-14">
          <h2 className="mb-5 font-heading text-2xl font-bold md:text-3xl">{t("home.featured")}</h2>
          <ProductGrid products={featured.data.products} currency={currency} />
        </section>
      )}

      {newest.ok && newest.data.products.length > 0 && (
        <section className="container-page mt-14">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="font-heading text-2xl font-bold md:text-3xl">{t("home.new")}</h2>
            <Link href="/search?sort=newest" className="text-sm font-semibold text-primary-700">
              {t("home.view_all")}
            </Link>
          </div>
          <ProductGrid products={newest.data.products} currency={currency} />
        </section>
      )}
    </>
  );
}
