import "server-only";

import type { ApiResult } from "./types";

/**
 * Server-side ERPNext client. Credentials never reach the browser: this module is server-only
 * and the API key/secret are plain (non NEXT_PUBLIC_) environment variables.
 */
const BASE_URL = (process.env.ERP_BASE_URL || "").replace(/\/$/, "");
const API_KEY = process.env.ERP_API_KEY || "";
const API_SECRET = process.env.ERP_API_SECRET || "";
/** When ERP_BASE_URL is http://127.0.0.1:8000 (gunicorn on the same VPS), tell Frappe which site. */
const SITE_NAME = process.env.ERP_SITE_NAME || "";
const TIMEOUT_MS = Number(process.env.ERP_TIMEOUT_MS || 15000);

export const CACHE_TAGS = { catalog: "catalog", products: "products", config: "config" } as const;

type CallOptions = {
  method?: "GET" | "POST";
  params?: Record<string, string | number | boolean | string[] | undefined | null>;
  body?: unknown;
  /** ISR: seconds to cache GET responses; false = cache until revalidated by tag */
  revalidate?: number | false;
  tags?: string[];
  clientIp?: string;
};

export async function callErp<T>(endpoint: string, options: CallOptions = {}): Promise<ApiResult<T>> {
  if (!BASE_URL || !API_KEY || !API_SECRET) {
    throw new Error("ERP_BASE_URL, ERP_API_KEY and ERP_API_SECRET must be set (or ERP_MOCK=1 for local dev)");
  }
  const method = options.method ?? "GET";
  const url = new URL(`${BASE_URL}/api/method/store_core.api.v1.${endpoint}`);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length)) continue;
    url.searchParams.set(key, Array.isArray(value) ? value.join(",") : String(value));
  }

  const headers: Record<string, string> = {
    Authorization: `token ${API_KEY}:${API_SECRET}`,
    Accept: "application/json",
  };
  if (SITE_NAME) headers["X-Frappe-Site-Name"] = SITE_NAME;
  if (options.clientIp) headers["X-Lamsa-Client-IP"] = options.clientIp;
  if (method === "POST") headers["Content-Type"] = "application/json";

  const cacheOptions: RequestInit =
    method === "GET"
      ? { next: { revalidate: options.revalidate ?? 300, tags: options.tags ?? [CACHE_TAGS.catalog] } }
      : { cache: "no-store" };

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: method === "POST" ? JSON.stringify(options.body ?? {}) : undefined,
      signal: AbortSignal.timeout(TIMEOUT_MS),
      ...cacheOptions,
    });
  } catch (error) {
    console.error(`[erp] ${endpoint} network error`, error);
    return { ok: false, error: { code: "network" }, status: 503 };
  }

  if (response.status === 429) return { ok: false, error: { code: "rate_limited" }, status: 429 };

  let payload: { message?: ApiResult<T>; exc_type?: string } | null = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (payload?.message && typeof payload.message === "object" && "ok" in payload.message) {
    return payload.message.ok ? payload.message : { ...payload.message, status: response.status };
  }
  console.error(`[erp] ${endpoint} failed`, response.status, payload?.exc_type);
  const code = response.status === 403 ? "forbidden" : response.status === 404 ? "not_found" : "generic";
  return { ok: false, error: { code }, status: response.status >= 400 ? response.status : 502 };
}
