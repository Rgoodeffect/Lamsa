import type { NextRequest } from "next/server";

import { badRequest, clientIp, limited, readJson, respond } from "@/lib/api-route";
import { verifyMoamalatPayment } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/**
 * POST the Moamalat Lightbox result. The browser is the only place that sees the gateway's
 * response, so it has to travel through here — but nothing in it is trusted: ERPNext recomputes
 * its SecureHash with the merchant secret and checks the amount before booking any money.
 */
export async function POST(req: NextRequest) {
  const blocked = await limited(req, "payment", limits.payment);
  if (blocked) return blocked;
  const body = await readJson(req);
  const payload = body?.payload;
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return badRequest();
  return respond(await verifyMoamalatPayment(payload as Record<string, unknown>, clientIp(req)));
}
