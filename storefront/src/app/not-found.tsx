import Link from "next/link";

import { t } from "@/lib/i18n";

export default function NotFound() {
  return (
    <div className="container-page py-24 text-center">
      <p className="font-heading text-6xl font-bold text-primary-300">404</p>
      <h1 className="mt-4 font-heading text-2xl font-bold">{t("errors.not_found_title")}</h1>
      <p className="mt-2 text-muted">{t("errors.not_found_text")}</p>
      <Link href="/" className="btn btn-primary mt-6">
        {t("errors.back_home")}
      </Link>
    </div>
  );
}
