"use client";

import type { ApiError, ApiResult } from "./erp/types";
import { tDynamic } from "./i18n";

export async function postJson<T>(url: string, body: unknown, signal?: AbortSignal): Promise<ApiResult<T>> {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    const data = (await res.json().catch(() => null)) as ApiResult<T> | null;
    if (data && typeof data === "object" && "ok" in data) return data.ok ? data : { ...data, status: res.status };
    return { ok: false, error: { code: "generic" }, status: res.status };
  } catch (error) {
    if ((error as Error)?.name === "AbortError") throw error;
    return { ok: false, error: { code: "network" } };
  }
}

/** Arabic message for a backend/route error code. */
export function errorMessage(error: ApiError): string {
  const details = Object.fromEntries(Object.entries(error.details ?? {}).map(([k, v]) => [k, v]));
  return tDynamic(`errors.${error.code}`, "errors.generic", details);
}
