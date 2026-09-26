import type { FeedItem } from "./erp/types";

/** Meta Commerce Manager catalog columns (https://www.facebook.com/business/help/120325381656392). */
export const META_COLUMNS = [
  "id",
  "item_group_id",
  "title",
  "description",
  "availability",
  "condition",
  "price",
  "sale_price",
  "link",
  "image_link",
  "additional_image_link",
  "brand",
  "size",
  "color",
  "gender",
  "age_group",
  "product_type",
] as const;

export type FeedRow = Record<(typeof META_COLUMNS)[number], string>;

export function toFeedRows(
  items: FeedItem[],
  siteUrl: string,
  media: (path: string | null | undefined) => string | null,
): FeedRow[] {
  return items.map((item) => ({
    id: item.id,
    item_group_id: item.item_group_id,
    title: item.title.slice(0, 200),
    description: item.description.slice(0, 9999),
    availability: item.availability,
    condition: item.condition || "new",
    price: item.price,
    sale_price: item.sale_price || "",
    link: `${siteUrl}/p/${encodeURIComponent(item.slug)}`,
    image_link: media(item.image_link) ?? "",
    additional_image_link: (item.additional_image_link || "")
      .split(",")
      .filter(Boolean)
      .map((p) => media(p) ?? "")
      .filter(Boolean)
      .join(","),
    brand: item.brand,
    size: item.size || "",
    color: item.color || "",
    gender: item.gender || "",
    age_group: item.age_group || "",
    product_type: item.product_type || "",
  }));
}

const csvCell = (value: string) => (/[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value);

export function toCsv(rows: FeedRow[]): string {
  const lines = [META_COLUMNS.join(",")];
  for (const row of rows) lines.push(META_COLUMNS.map((c) => csvCell(row[c] ?? "")).join(","));
  // BOM so Excel opens Arabic correctly; Meta accepts UTF-8 with BOM
  return "﻿" + lines.join("\n") + "\n";
}

const xmlEscape = (value: string) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    // strip characters that are invalid in XML 1.0
    .replace(/[^\u0009\u000A\u000D -퟿-�]/g, "");

/** RSS 2.0 with the g: namespace, the XML format Meta accepts for catalogs. */
export function toRssXml(rows: FeedRow[], meta: { title: string; link: string; description: string }): string {
  const items = rows
    .map((row) => {
      const fields = META_COLUMNS.filter((c) => row[c])
        .map((c) => {
          if (c === "additional_image_link") {
            return row[c]
              .split(",")
              .map((url) => `      <g:additional_image_link>${xmlEscape(url)}</g:additional_image_link>`)
              .join("\n");
          }
          return `      <g:${c}>${xmlEscape(row[c])}</g:${c}>`;
        })
        .join("\n");
      return `    <item>\n${fields}\n    </item>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>${xmlEscape(meta.title)}</title>
    <link>${xmlEscape(meta.link)}</link>
    <description>${xmlEscape(meta.description)}</description>
${items}
  </channel>
</rss>
`;
}
