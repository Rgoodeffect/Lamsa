import { publicEnv } from "@/lib/env";
import { toRssXml } from "@/lib/feed";
import { metaFeedRows } from "@/lib/feed-response";
import { t } from "@/lib/i18n";

/** Meta Commerce Manager data feed (RSS/XML). */
export const revalidate = 3600;

export async function GET() {
  const rows = await metaFeedRows();
  if (!rows) return new Response("feed unavailable", { status: 503 });
  const xml = toRssXml(rows, { title: t("brand.name"), link: publicEnv.siteUrl, description: t("brand.description") });
  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=900" },
  });
}
