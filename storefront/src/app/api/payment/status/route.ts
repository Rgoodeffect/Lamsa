import type { NextRequest } from "next/server";

import { badRequest, clientIp, limited, readJson, respond, str } from "@/lib/api-route";
import { getPaymentStatus } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/** POST {order_no, event_id}: has this order been paid? Used while the gateway callback lands. */
export async function POST(req: NextRequest) {
  const blocked = await limited(req, "payment", limits.payment);
  if (blocked) return blocked;
  const body = await readJson(req);
  const orderNo = str(body?.order_no, 30);
  const eventId = str(body?.event_id, 64);
  if (!orderNo || !eventId) return badRequest();
  return respond(await getPaymentStatus(orderNo, eventId, clientIp(req)));
}
