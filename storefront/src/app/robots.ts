import type { MetadataRoute } from "next";

import { publicEnv } from "@/lib/env";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/cart", "/checkout", "/order/", "/track", "/api/"] },
    sitemap: `${publicEnv.siteUrl}/sitemap.xml`,
  };
}
