import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { normalizeLibyanPhone } from "@/lib/phone";

// Same cases as the Python implementation (store_core/utils/phone.py)
const cases = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../store_core/tests/unit/phone_cases.json"), "utf-8"),
) as { valid: [string, string][]; invalid: string[] };

describe("normalizeLibyanPhone", () => {
  it.each(cases.valid)("normalizes %s", (raw, expected) => {
    expect(normalizeLibyanPhone(raw)).toBe(expected);
  });
  it.each(cases.invalid)("rejects %s", (raw) => {
    expect(normalizeLibyanPhone(raw)).toBeNull();
  });
});
