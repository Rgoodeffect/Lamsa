// i18n-allow: Arabic-Indic digit table for parsing, not UI text
/**
 * Libyan mobile validation/normalization — mirrors store_core/utils/phone.py.
 * Both implementations are tested against store_core/tests/unit/phone_cases.json.
 */
const COUNTRY_CODE = "218";
const MOBILE_PREFIXES = ["91", "92", "93", "94", "95"];
const EASTERN_DIGITS = "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹";
const STRIP = /[\s\-.()‎‏‪-‮]/g;

export function normalizeLibyanPhone(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let value = Array.from(String(raw))
    .map((ch) => {
      const i = EASTERN_DIGITS.indexOf(ch);
      return i === -1 ? ch : String(i % 10);
    })
    .join("")
    .replace(STRIP, "");

  if (value.startsWith("+")) {
    value = value.slice(1);
    if (!value.startsWith(COUNTRY_CODE)) return null;
  } else if (value.startsWith("00")) {
    value = value.slice(2);
    if (!value.startsWith(COUNTRY_CODE)) return null;
  }
  if (!/^\d+$/.test(value)) return null;

  let national: string;
  if (value.startsWith(COUNTRY_CODE) && value.length === 12) national = value.slice(3);
  else if (value.startsWith("0") && value.length === 10) national = value.slice(1);
  else if (value.length === 9) national = value;
  else return null;

  if (!MOBILE_PREFIXES.includes(national.slice(0, 2))) return null;
  return `+${COUNTRY_CODE}${national}`;
}

export const isValidLibyanPhone = (raw: string | null | undefined) => normalizeLibyanPhone(raw) !== null;
