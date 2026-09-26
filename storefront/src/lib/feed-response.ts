import "server-only";

import { mediaUrl, publicEnv } from "./env";
import { getMetaFeed } from "./erp";
import { toFeedRows } from "./feed";

export async function metaFeedRows() {
  const res = await getMetaFeed();
  if (!res.ok) return null;
  // Meta rejects items without an image, so they are left out of the feed
  return toFeedRows(res.data.items, publicEnv.siteUrl, mediaUrl).filter((row) => row.image_link);
}
