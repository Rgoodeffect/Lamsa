import type { MetadataRoute } from "next";

import { publicEnv } from "@/lib/env";
import { getSitemap } from "@/lib/erp";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = publicEnv.siteUrl;
  const res = await getSitemap();
  const entries: MetadataRoute.Sitemap = [
    { url: `${base}/`, changeFrequency: "daily", priority: 1 },
    { url: `${base}/offers`, changeFrequency: "daily", priority: 0.9 },
  ];
  if (!res.ok) return entries;
  for (const slug of res.data.categories) {
    entries.push({ url: `${base}/c/${encodeURIComponent(slug)}`, changeFrequency: "daily", priority: 0.8 });
  }
  for (const p of res.data.products) {
    entries.push({
      url: `${base}/p/${encodeURIComponent(p.slug)}`,
      lastModified: new Date(p.updated.replace(" ", "T")),
      changeFrequency: "weekly",
      priority: 0.6,
    });
  }
  return entries;
}
