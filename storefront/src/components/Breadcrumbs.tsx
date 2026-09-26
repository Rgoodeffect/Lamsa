import Link from "next/link";

import type { Breadcrumb } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

export function Breadcrumbs({ items, current }: { items: Breadcrumb[]; current?: string }) {
  return (
    <nav aria-label={t("nav.breadcrumb")} className="text-sm text-muted">
      <ol className="flex flex-wrap items-center gap-1.5">
        <li>
          <Link href="/" className="hover:text-primary-700">
            {t("nav.home")}
          </Link>
        </li>
        {items.map((b) => (
          <li key={b.slug} className="flex items-center gap-1.5">
            <span aria-hidden>‹</span>
            <Link href={`/c/${b.slug}`} className="hover:text-primary-700">
              {b.title}
            </Link>
          </li>
        ))}
        {current && (
          <li className="flex items-center gap-1.5 text-ink" aria-current="page">
            <span aria-hidden>‹</span>
            {current}
          </li>
        )}
      </ol>
    </nav>
  );
}
