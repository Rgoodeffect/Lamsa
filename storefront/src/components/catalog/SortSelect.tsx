"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { t } from "@/lib/i18n";
import { SORTS } from "@/lib/search-params";

export function SortSelect() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted">{t("sort.label")}</span>
      <select
        className="rounded-xl border border-line bg-surface px-3 py-2"
        value={params.get("sort") ?? "featured"}
        onChange={(e) => {
          const next = new URLSearchParams(params.toString());
          next.set("sort", e.target.value);
          next.delete("page");
          router.push(`${pathname}?${next.toString()}`, { scroll: false });
        }}
      >
        {SORTS.map((s) => (
          <option key={s} value={s}>
            {t(`sort.${s}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
