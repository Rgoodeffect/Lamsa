"use client";

import { t } from "@/lib/i18n";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container-page py-24 text-center">
      <h1 className="font-heading text-2xl font-bold">{t("errors.generic")}</h1>
      <button type="button" onClick={reset} className="btn btn-primary mt-6">
        {t("errors.retry")}
      </button>
    </div>
  );
}
