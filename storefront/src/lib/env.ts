/** Public (browser-safe) settings. Server secrets are read in src/lib/erp/client.ts only. */
export const publicEnv = {
  siteUrl: (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/$/, ""),
  erpPublicUrl: (process.env.NEXT_PUBLIC_ERP_PUBLIC_URL || "").replace(/\/$/, ""),
  metaPixelId: process.env.NEXT_PUBLIC_META_PIXEL_ID || "",
  whatsappNumber: (process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || "").replace(/\D/g, ""),
};

/** ERPNext file paths ("/files/x.jpg") -> absolute URL on the ERP public host. */
export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path) || !path.startsWith("/files/")) return path;
  return `${publicEnv.erpPublicUrl}${path}`;
}
