import { t } from "@/lib/i18n";

export default function Loading() {
  return (
    <div className="container-page py-10" aria-busy="true" aria-label={t("common.loading")}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => (
          <div key={i} className="aspect-[4/5] animate-pulse rounded-card bg-primary-100/60" />
        ))}
      </div>
    </div>
  );
}
