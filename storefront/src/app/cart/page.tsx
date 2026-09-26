import type { Metadata } from "next";

import { CartView } from "@/components/cart/CartView";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("cart.title"), robots: { index: false } };

export default function CartPage() {
  return (
    <div className="container-page py-8">
      <h1 className="mb-6 font-heading text-3xl font-bold">{t("cart.title")}</h1>
      <CartView />
    </div>
  );
}
