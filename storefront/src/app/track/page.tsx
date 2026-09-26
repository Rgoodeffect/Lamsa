import type { Metadata } from "next";

import { TrackForm } from "@/components/track/TrackForm";
import { t } from "@/lib/i18n";

export const metadata: Metadata = { title: t("track.title"), robots: { index: false } };

export default async function TrackPage({ searchParams }: PageProps<"/track">) {
  const sp = await searchParams;
  const order = typeof sp.order === "string" ? sp.order.slice(0, 30) : "";
  return (
    <div className="container-page max-w-xl py-10">
      <h1 className="font-heading text-3xl font-bold">{t("track.title")}</h1>
      <p className="mt-2 text-muted">{t("track.intro")}</p>
      <TrackForm initialOrderNo={order} />
    </div>
  );
}
