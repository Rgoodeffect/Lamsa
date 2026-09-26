import type { NextRequest } from "next/server";

import { badRequest, cartItems, clientIp, limited, readJson, respond, str } from "@/lib/api-route";
import { quoteCart } from "@/lib/erp";
import { limits } from "@/lib/rate-limit";

/** POST {items:[{item_code, qty}], zone?, gift_wrap?, coupon_code?} -> server-calculated totals */
export async function POST(req: NextRequest) {
  const blocked = await limited(req, "quote", limits.quote);
  if (blocked) return blocked;
  const body = await readJson(req);
  const items = cartItems(body?.items);
  if (!body || !items) return badRequest();
  return respond(
    await quoteCart(
      {
        items,
        zone: str(body.zone, 140),
        gift_wrap: body.gift_wrap === true,
        coupon_code: str(body.coupon_code, 40),
      },
      clientIp(req),
    ),
  );
}
