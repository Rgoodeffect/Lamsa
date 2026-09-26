import type { NextRequest } from "next/server";

import { badRequest, cartItems, clientIp, limited, readJson, respond, str } from "@/lib/api-route";
import { placeOrder } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/** POST guest checkout. All prices/fees are recalculated by ERPNext; only choices are sent. */
export async function POST(req: NextRequest) {
  const blocked = limited(req, "checkout", limits.checkout);
  if (blocked) return blocked;
  const body = await readJson(req);
  const items = cartItems(body?.items);
  if (!body || !items) return badRequest();
  return respond(
    await placeOrder(
      {
        items,
        full_name: str(body.full_name, 140) ?? "",
        phone: str(body.phone, 30) ?? "",
        zone: str(body.zone, 140) ?? "",
        event_id: str(body.event_id, 64) ?? "",
        address_notes: str(body.address_notes, 500),
        gift_wrap: body.gift_wrap === true,
        gift_message: str(body.gift_message, 500),
        payment_provider: str(body.payment_provider, 40),
      },
      clientIp(req),
    ),
  );
}
