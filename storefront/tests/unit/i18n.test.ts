import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { t } from "@/lib/i18n";
import messages from "../../messages/ar.json";

const SRC = path.resolve(__dirname, "../../src");
const ARABIC = /[؀-ۿ]/;
// Sample catalog data for ERP_MOCK is data, not UI text.
const ALLOWED = new Set([path.join(SRC, "lib/erp/mock-data.ts")]);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return files(full);
    return /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}

describe("translations", () => {
  it("has no hard-coded Arabic text in src/ (use messages/ar.json)", () => {
    const offenders = files(SRC).filter((f) => {
      const text = readFileSync(f, "utf-8");
      // a file may opt out with a first-line "// i18n-allow: <reason>" (parsing tables, not UI text)
      return !ALLOWED.has(f) && !text.startsWith("// i18n-allow:") && ARABIC.test(text);
    });
    expect(offenders).toEqual([]);
  });

  it("every t(\"key\") used in src/ exists in ar.json", () => {
    const missing: string[] = [];
    for (const f of files(SRC)) {
      for (const m of readFileSync(f, "utf-8").matchAll(/\bt\(\s*"([\w.\s-]+)"/g)) {
        if (!(m[1] in messages)) missing.push(`${path.relative(SRC, f)}: ${m[1]}`);
      }
    }
    expect(missing).toEqual([]);
  });

  it("interpolates variables", () => {
    expect(t("errors.qty_limit", { max_qty: 5 })).toContain("5");
    expect(t("pagination.page", { page: 2, pages: 3 })).toMatch(/2.*3/);
  });

  it("has a message for every error code the backend can return", () => {
    const codes = [
      "cart_empty", "cart_too_large", "invalid_item", "item_unavailable", "variant_required", "qty_limit",
      "out_of_stock", "invalid_zone", "invalid_name", "invalid_phone", "address_notes_too_long",
      "gift_message_too_long", "invalid_event_id", "payment_unavailable", "order_not_found",
      "product_not_found", "category_not_found", "invalid_request", "rate_limited", "network",
    ];
    expect(codes.filter((c) => !(`errors.${c}` in messages))).toEqual([]);
  });
});
