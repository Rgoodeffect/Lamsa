import messages from "../../messages/ar.json";

/**
 * All customer-facing text comes from messages/ar.json.
 * `t("cart.title")` or `t("errors.qty_limit", { max_qty: 5 })`.
 */
export type MessageKey = keyof typeof messages;

export const locale = "ar-LY";
export const dir = "rtl";

export function t(key: MessageKey, vars?: Record<string, string | number | null | undefined>): string {
  const template: string = messages[key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    vars[name] === undefined || vars[name] === null ? match : String(vars[name]),
  );
}

/** Translate a dynamic key (error codes, statuses) with a safe fallback. */
export function tDynamic(key: string, fallback: MessageKey, vars?: Record<string, string | number>): string {
  return key in messages ? t(key as MessageKey, vars) : t(fallback, vars);
}
