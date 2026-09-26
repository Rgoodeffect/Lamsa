import "server-only";

/**
 * Fixed-window rate limiter for the public API routes (the first of two layers; ERPNext enforces
 * its own limit per forwarded IP).
 *
 * Redis-backed when REDIS_URL is set, so the limit is shared by every Next.js process and survives
 * a restart. Without Redis — and whenever Redis is unreachable — it falls back to an in-memory
 * window, which is correct for a single process (PM2 fork mode) and degrades to a per-process limit
 * for several. Failing open is deliberate: a Redis outage must slow the store down, not close it.
 */
import type { Redis } from "ioredis";

type Window = { count: number; resetAt: number };
type Decision = { ok: boolean; retryAfter: number };

const windows = new Map<string, Window>();
const KEY_PREFIX = "lamsa:rl:";

let client: Redis | null | undefined;
let redisWarned = false;

/** One lazily created connection per process. `undefined` = not tried yet, `null` = no Redis. */
async function redis(): Promise<Redis | null> {
  if (client !== undefined) return client;
  const url = process.env.REDIS_URL;
  if (!url) {
    client = null;
    return client;
  }
  // Imported on first use, not at module load, so a build without Redis never touches the driver.
  const { default: Redis } = await import("ioredis");
  client = new Redis(url, {
    lazyConnect: false,
    enableOfflineQueue: false,
    maxRetriesPerRequest: 1,
    connectTimeout: 1000,
    keyPrefix: KEY_PREFIX,
  });
  client.on("error", (error: Error) => {
    if (redisWarned) return;
    redisWarned = true;
    console.error("[rate-limit] Redis unavailable, falling back to in-memory limiting:", error.message);
  });
  return client;
}

export async function rateLimit(key: string, limit: number, windowMs: number): Promise<Decision> {
  const shared = await redis();
  if (shared) {
    try {
      return await redisWindow(shared, key, limit, windowMs);
    } catch {
      // fall through to the in-memory window
    }
  }
  return memoryWindow(key, limit, windowMs);
}

/**
 * INCR the counter and give it a TTL the first time it appears: the key expiring *is* the window
 * rolling over, so no timestamps have to be stored or compared.
 *
 * The TTL is set with a plain EXPIRE rather than `EXPIRE ... NX`, which needs Redis 7, so this works
 * against whatever Redis the bench already runs. Two simultaneous first hits can both set it, to the
 * same value — the same trade-off the ERPNext-side limiter makes.
 */
async function redisWindow(shared: Redis, key: string, limit: number, windowMs: number): Promise<Decision> {
  const seconds = Math.ceil(windowMs / 1000);
  const replies = await shared.multi().incr(key).ttl(key).exec();
  const count = Number(replies?.[0]?.[1] ?? 0);
  let ttl = Number(replies?.[1]?.[1] ?? -1);
  if (count === 1 || ttl < 0) {
    await shared.expire(key, seconds);
    ttl = seconds;
  }
  return { ok: count <= limit, retryAfter: ttl > 0 ? ttl : seconds };
}

function memoryWindow(key: string, limit: number, windowMs: number): Decision {
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
  payment: { limit: Number(process.env.RATE_LIMIT_PAYMENT_PER_10MIN || 20), windowMs: 10 * 60_000 },
  // Encoding an image costs real CPU on the same box as ERPNext, so this is the tightest limit.
  imageSearch: { limit: Number(process.env.RATE_LIMIT_IMAGE_SEARCH_PER_5MIN || 10), windowMs: 5 * 60_000 },
};

/** Test seam: forget the in-memory windows and the cached connection. */
export function resetRateLimits() {
  windows.clear();
  client?.disconnect();
  client = undefined;
  redisWarned = false;
}
