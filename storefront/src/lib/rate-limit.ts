import "server-only";

/**
 * Fixed-window rate limiter for the public API routes (first layer).
 * In-memory is correct for a single Next.js process (PM2 fork mode, as in the README).
 * ERPNext enforces a second, Redis-backed limit per client IP on checkout/track/quote,
 * so running several Next processes can only loosen this layer, never remove limiting.
 */
type Window = { count: number; resetAt: number };
const windows = new Map<string, Window>();

export function rateLimit(key: string, limit: number, windowMs: number): { ok: boolean; retryAfter: number } {
  const now = Date.now();
  if (windows.size > 50_000) {
    for (const [k, w] of windows) if (w.resetAt <= now) windows.delete(k);
  }
  const current = windows.get(key);
  if (!current || current.resetAt <= now) {
    windows.set(key, { count: 1, resetAt: now + windowMs });
    return { ok: true, retryAfter: 0 };
  }
  current.count += 1;
  return { ok: current.count <= limit, retryAfter: Math.ceil((current.resetAt - now) / 1000) };
}

export const limits = {
  checkout: { limit: Number(process.env.RATE_LIMIT_CHECKOUT_PER_10MIN || 5), windowMs: 10 * 60_000 },
  track: { limit: Number(process.env.RATE_LIMIT_TRACK_PER_5MIN || 10), windowMs: 5 * 60_000 },
  quote: { limit: Number(process.env.RATE_LIMIT_QUOTE_PER_MIN || 60), windowMs: 60_000 },
};
