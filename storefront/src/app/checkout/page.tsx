import type { Metadata } from "next";

import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { getStoreConfig, getZones } from "@/lib/erp";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("checkout.title"), robots: { index: false } };

// Rendered per request (zones and fees must be current); the ERP fetches themselves are cached.
export const dynamic = "force-dynamic";

export default async function CheckoutPage() {
  const [zones, config] = await Promise.all([getZones(), getStoreConfig()]);
  if (!zones.ok || !config.ok) throw new Error("checkout_config_unavailable");
  return (
    <div className="container-page py-8">
      <h1 className="font-heading text-3xl font-bold">{t("checkout.title")}</h1>
      <p className="mt-1 text-sm text-muted">{t("checkout.no_signup")}</p>
      <CheckoutForm zones={zones.data} config={config.data} />
    </div>
  );
}
