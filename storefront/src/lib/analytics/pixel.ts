"use client";

/**
 * Meta Pixel standard events. `eventId` lets Meta deduplicate the browser event with the
 * server-side Conversions API event (store_core/integrations/meta/capi.py) for Purchase.
 */
type PixelParams = {
  content_ids?: string[];
  content_type?: "product" | "product_group";
  contents?: { id: string; quantity: number; item_price?: number }[];
  value?: number;
  currency?: string;
  num_items?: number;
  content_name?: string;
};

type Fbq = (command: string, event: string, params?: PixelParams, options?: { eventID?: string }) => void;

export function trackPixel(
  event: "ViewContent" | "AddToCart" | "InitiateCheckout" | "Purchase",
  params: PixelParams,
  eventId?: string,
) {
  const fbq = (globalThis as unknown as { fbq?: Fbq }).fbq;
  if (typeof fbq !== "function") return;
  fbq("track", event, params, eventId ? { eventID: eventId } : undefined);
}

export function newEventId(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
