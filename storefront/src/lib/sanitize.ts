/**
 * Defense-in-depth for product descriptions authored in ERPNext's Text Editor.
 * Frappe already sanitizes on save; this strips anything executable that might slip through.
 */
export function sanitizeHtml(html: string | null | undefined): string {
  if (!html) return "";
  return html
    .replace(/<\s*(script|style|iframe|object|embed|form|link|meta)[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi, "")
    .replace(/<\s*(script|style|iframe|object|embed|form|link|meta)[^>]*\/?>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/(href|src)\s*=\s*("|')\s*javascript:[^"']*\2/gi, '$1="#"');
}

export function plainText(html: string | null | undefined, max = 160): string {
  const text = (html ?? "").replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
