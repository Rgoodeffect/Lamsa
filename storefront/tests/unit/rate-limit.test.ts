import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { limits, rateLimit, resetRateLimits } from "@/lib/rate-limit";

/**
 * Without REDIS_URL the limiter uses its in-memory window, which is what these tests exercise.
 * The Redis path is a shared counter with a TTL and is covered by the fallback test below: whatever
 * goes wrong with Redis, requests must keep being served.
 */
describe("in-memory rate limiting", () => {
  beforeEach(() => {
    delete process.env.REDIS_URL;
    resetRateLimits();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    resetRateLimits();
  });

  it("allows exactly `limit` requests in a window", async () => {
    for (let i = 0; i < 3; i++) {
      expect((await rateLimit("k", 3, 60_000)).ok, `request ${i + 1}`).toBe(true);
    }
    expect((await rateLimit("k", 3, 60_000)).ok).toBe(false);
  });

  it("reports how long to wait", async () => {
    await rateLimit("k", 1, 60_000);
    const blocked = await rateLimit("k", 1, 60_000);
    expect(blocked.ok).toBe(false);
    expect(blocked.retryAfter).toBeGreaterThan(0);
    expect(blocked.retryAfter).toBeLessThanOrEqual(60);
  });

  it("starts a fresh window once the old one has passed", async () => {
    await rateLimit("k", 1, 60_000);
    expect((await rateLimit("k", 1, 60_000)).ok).toBe(false);
    vi.advanceTimersByTime(60_001);
    expect((await rateLimit("k", 1, 60_000)).ok).toBe(true);
  });

  it("counts each key on its own, so one shopper cannot block another", async () => {
    await rateLimit("checkout:1.1.1.1", 1, 60_000);
    expect((await rateLimit("checkout:1.1.1.1", 1, 60_000)).ok).toBe(false);
    expect((await rateLimit("checkout:2.2.2.2", 1, 60_000)).ok).toBe(true);
  });

  it("keeps serving when Redis cannot be reached", async () => {
    // A port nothing listens on: connecting fails, and the limiter must fall back rather than throw.
    process.env.REDIS_URL = "redis://127.0.0.1:1/0";
    resetRateLimits();
    await expect(rateLimit("k", 1, 60_000)).resolves.toMatchObject({ ok: true });
  });

  it("has a limit for every public route", () => {
    for (const name of ["checkout", "track", "quote", "payment"] as const) {
      expect(limits[name].limit, name).toBeGreaterThan(0);
      expect(limits[name].windowMs, name).toBeGreaterThan(0);
    }
  });
});
