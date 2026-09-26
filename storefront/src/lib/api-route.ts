import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import type { ApiResult } from "./erp/types";
import { rateLimit } from "./rate-limit";

/** Shopper IP as seen by nginx (X-Real-IP / first X-Forwarded-For hop). */
export function clientIp(req: NextRequest): string {
  const real = req.headers.get("x-real-ip");
  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0];
  return (real || forwarded || "unknown").trim().slice(0, 64);
}

export function limited(req: NextRequest, name: string, cfg: { limit: number; windowMs: number }) {
  const r = rateLimit(`${name}:${clientIp(req)}`, cfg.limit, cfg.windowMs);
  if (r.ok) return null;
  return NextResponse.json(
    { ok: false, error: { code: "rate_limited" } },
    { status: 429, headers: { "Retry-After": String(r.retryAfter) } },
  );
}

export async function readJson(req: NextRequest): Promise<Record<string, unknown> | null> {
  if (Number(req.headers.get("content-length") || 0) > 32_000) return null;
  try {
    const body = await req.json();
    return body && typeof body === "object" && !Array.isArray(body) ? body : null;
  } catch {
    return null;
  }
}

export function respond<T>(result: ApiResult<T>) {
  if (result.ok) return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
  return NextResponse.json({ ok: false, error: result.error }, { status: result.status ?? 422 });
}

export const badRequest = () => NextResponse.json({ ok: false, error: { code: "invalid_request" } }, { status: 400 });

export function cartItems(value: unknown): { item_code: string; qty: number }[] | null {
  if (!Array.isArray(value) || value.length > 30) return null;
  const items = value.map((row) => ({
    item_code: String((row as { item_code?: unknown })?.item_code ?? "").slice(0, 140),
    qty: Math.floor(Number((row as { qty?: unknown })?.qty)),
  }));
  return items.every((i) => i.item_code && i.qty > 0 && i.qty < 1000) ? items : null;
}

const str = (v: unknown, max: number) => (typeof v === "string" ? v.slice(0, max) : undefined);
export { str };
