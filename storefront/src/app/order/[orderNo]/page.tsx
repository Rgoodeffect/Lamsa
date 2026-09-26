import type { Metadata } from "next";

import { OrderConfirmation } from "@/components/checkout/OrderConfirmation";
import { t } from "@/lib/i18n";
import { decodeSlug } from "@/lib/search-params";

export const metadata: Metadata = { title: t("order.thanks"), robots: { index: false } };

export default async function OrderPage({ params }: PageProps<"/order/[orderNo]">) {
  const { orderNo } = await params;
  return (
    <div className="container-page py-10">
      <OrderConfirmation orderNo={decodeSlug(orderNo)} />
    </div>
  );
}
