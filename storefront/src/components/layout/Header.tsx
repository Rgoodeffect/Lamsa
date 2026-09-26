import Link from "next/link";

import type { Category } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

import { SearchIcon } from "../Icons";
import { CartButton } from "./CartButton";
import { MobileMenu } from "./MobileMenu";

export function Header({ categories }: { categories: Category[] }) {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-cream/95 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:start-2 focus:top-2 btn btn-primary">
        {t("nav.skip_to_content")}
      </a>
      <div className="container-page flex h-16 items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <MobileMenu categories={categories} />
          <Link href="/" className="font-heading text-3xl font-bold text-primary-600" aria-label={t("brand.name")}>
            {t("brand.name")}
          </Link>
        </div>

        <nav aria-label={t("nav.categories")} className="hidden md:block">
          <ul className="flex items-center gap-6 text-[0.95rem] font-medium">
            {categories.map((c) => (
              <li key={c.slug}>
                <Link href={`/c/${c.slug}`} className="py-2 hover:text-primary-600">
                  {c.title}
                </Link>
              </li>
            ))}
            <li>
              <Link href="/offers" className="py-2 font-semibold text-danger hover:text-danger/80">
                {t("nav.offers")}
              </Link>
            </li>
          </ul>
        </nav>

        <div className="flex items-center gap-1">
          <Link href="/search" className="rounded-full p-2.5 hover:bg-primary-50" aria-label={t("nav.search")}>
            <SearchIcon />
          </Link>
          <CartButton />
        </div>
      </div>
    </header>
  );
}
