import { toCsv } from "@/lib/feed";
import { metaFeedRows } from "@/lib/feed-response";

/** Meta Commerce Manager data feed (CSV). Schedule it in Commerce Manager: /feeds/meta.csv */
export const revalidate = 3600;

export async function GET() {
  const rows = await metaFeedRows();
  if (!rows) return new Response("feed unavailable", { status: 503 });
  return new Response(toCsv(rows), {
    headers: { "Content-Type": "text/csv; charset=utf-8", "Cache-Control": "public, max-age=900" },
  });
}
