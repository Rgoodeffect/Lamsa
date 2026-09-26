import type { NextRequest } from "next/server";

import { badRequest, clientIp, limited, respond } from "@/lib/api-route";
import { searchByImage } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/** Uploads are larger than the other routes' bodies, so this one reads the body itself. */
const MAX_BYTES = 8 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/avif", "image/gif"]);

/**
 * POST multipart/form-data with an `image` file -> products that look like it.
 * The file is forwarded to ERPNext as base64, encoded there and discarded; nothing is stored.
 */
export async function POST(req: NextRequest) {
  const blocked = await limited(req, "image_search", limits.imageSearch);
  if (blocked) return blocked;

  if (Number(req.headers.get("content-length") || 0) > MAX_BYTES + 64 * 1024) {
    return respond({ ok: false, error: { code: "image_too_large" }, status: 413 });
  }

  let file: File | null = null;
  try {
    const form = await req.formData();
    const value = form.get("image");
    file = value instanceof File ? value : null;
  } catch {
    return badRequest();
  }
  if (!file || !file.size) return badRequest();
  if (file.size > MAX_BYTES) return respond({ ok: false, error: { code: "image_too_large" }, status: 413 });
  // Trust the declared type only to reject early; ERPNext decodes the bytes and is the real check.
  if (file.type && !ALLOWED_TYPES.has(file.type)) {
    return respond({ ok: false, error: { code: "image_unreadable" }, status: 422 });
  }

  const base64 = Buffer.from(await file.arrayBuffer()).toString("base64");
  return respond(await searchByImage(base64, clientIp(req)));
}
