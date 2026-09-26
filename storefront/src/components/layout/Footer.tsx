import Link from "next/link";

import type { Category } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

export function Footer({ categories }: { categories: Category[] }) {
  return (
    <footer className="mt-16 border-t border-line bg-primary-50/60">
      <div className="container-page grid gap-8 py-10 sm:grid-cols-3">
        <div>
          <p className="font-heading text-2xl font-bold text-primary-600">{t("brand.name")}</p>
          <p className="mt-2 text-sm text-muted">{t("brand.description")}</p>
        </div>
        <div>
          <p className="mb-3 font-semibold">{t("nav.categories")}</p>
          <ul className="space-y-2 text-sm">
            {categories.map((c) => (
              <li key={c.slug}>
                <Link href={`/c/${c.slug}`} className="hover:text-primary-700">
                  {c.title}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-3 font-semibold">{t("footer.help")}</p>
          <ul className="space-y-2 text-sm">
            <li>
              <Link href="/offers" className="hover:text-primary-700">
                {t("nav.offers")}
              </Link>
            </li>
            <li>
              <Link href="/track" className="hover:text-primary-700">
                {t("nav.track")}
              </Link>
            </li>
            <li className="text-muted">{t("footer.cod")}</li>
          </ul>
        </div>
      </div>
      <p className="border-t border-line py-4 text-center text-xs text-muted">
        {t("footer.rights", { year: new Date().getFullYear() })}
      </p>
    </footer>
  );
}
