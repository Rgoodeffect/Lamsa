import { describe, expect, it } from "vitest";

import { formatPrice, formatPriceRange } from "@/lib/format";
import { sanitizeHtml } from "@/lib/sanitize";

describe("format", () => {
  it("formats LYD with western digits", () => {
    expect(formatPrice(250, "LYD")).toMatch(/^250 /);
    expect(formatPrice(1250.5, "LYD")).toMatch(/1,250.5/);
  });
  it("shows a range as 'from'", () => {
    expect(formatPriceRange(100, 100)).toBe(formatPrice(100));
    expect(formatPriceRange(100, 150)).toContain(formatPrice(100));
  });
});

describe("sanitizeHtml", () => {
  it("removes scripts and handlers", () => {
    const out = sanitizeHtml('<p onclick="x()">hi</p><script>alert(1)</script><a href="javascript:bad()">l</a>');
    expect(out).not.toMatch(/script|onclick|javascript:/);
    expect(out).toContain("<p>hi</p>");
  });
});
