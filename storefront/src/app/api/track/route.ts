import type { NextRequest } from "next/server";

import { badRequest, clientIp, limited, readJson, respond, str } from "@/lib/api-route";
import { trackOrder } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/** POST {order_no, phone} -> order status (same error for unknown order and wrong phone). */
export async function POST(req: NextRequest) {
  const blocked = limited(req, "track", limits.track);
  if (blocked) return blocked;
  const body = await readJson(req);
  const orderNo = str(body?.order_no, 30);
  const phone = str(body?.phone, 30);
  if (!orderNo || !phone) return badRequest();
  return respond(await trackOrder(orderNo, phone, clientIp(req)));
}
