import { timingSafeEqual } from "node:crypto";

import { revalidateTag } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

import { CACHE_TAGS } from "@/lib/erp/client";

/**
 * Called by ERPNext (store_core.services.revalidate) when items, prices, groups or stock change.
 * POST {tags: ["catalog" | "products" | "config"]} with "Authorization: Bearer <REVALIDATE_SECRET>".
 */
const ALLOWED = new Set<string>(Object.values(CACHE_TAGS));

function authorized(req: NextRequest): boolean {
  const secret = process.env.REVALIDATE_SECRET || "";
  const given = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!secret || given.length !== secret.length) return false;
  return timingSafeEqual(Buffer.from(given), Buffer.from(secret));
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) return NextResponse.json({ ok: false }, { status: 401 });
  const body = (await req.json().catch(() => ({}))) as { tags?: unknown };
  const tags = (Array.isArray(body.tags) ? body.tags : [CACHE_TAGS.catalog]).filter(
    (tag): tag is string => typeof tag === "string" && ALLOWED.has(tag),
  );
  // "catalog" changes can affect everything that lists products
  const expanded = new Set(tags.includes(CACHE_TAGS.catalog) ? [...tags, CACHE_TAGS.products] : tags);
  for (const tag of expanded) revalidateTag(tag, "max");
  return NextResponse.json({ ok: true, revalidated: [...expanded] });
}
