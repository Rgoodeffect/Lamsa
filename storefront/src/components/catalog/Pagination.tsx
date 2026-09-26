import Link from "next/link";

import type { Pagination as P } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

export function Pagination({ pagination, basePath, params }: { pagination: P; basePath: string; params: URLSearchParams }) {
  if (pagination.pages <= 1) return null;
  const href = (page: number) => {
    const next = new URLSearchParams(params);
    if (page > 1) next.set("page", String(page));
    else next.delete("page");
    const qs = next.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  };
  return (
    <nav className="mt-10 flex items-center justify-center gap-4" aria-label={t("pagination.page", pagination)}>
      {pagination.page > 1 && (
        <Link className="btn btn-outline py-2" href={href(pagination.page - 1)} rel="prev">
          {t("pagination.previous")}
        </Link>
      )}
      <span className="text-sm text-muted">{t("pagination.page", pagination)}</span>
      {pagination.page < pagination.pages && (
        <Link className="btn btn-outline py-2" href={href(pagination.page + 1)} rel="next">
          {t("pagination.next")}
        </Link>
      )}
    </nav>
  );
}
