import { describe, expect, it } from "vitest";

import { META_COLUMNS, toCsv, toFeedRows, toRssXml } from "@/lib/feed";

const items = [
  {
    id: "DRESS-M-BGE",
    item_group_id: "DRESS",
    title: 'Dress "Evening", embroidered',
    description: "Line1\nLine2 & <more>",
    availability: "in stock",
    condition: "new",
    price: "250.00 LYD",
    slug: "evening-dress",
    image_link: "/files/a.jpg",
    additional_image_link: "/files/b.jpg,/files/c.jpg",
    brand: "Lamsa",
    size: "M",
    color: "Beige",
    gender: "female",
    age_group: "adult",
    product_type: "Women > Dresses",
  },
];

const rows = toFeedRows(items, "https://lamsa.ly", (p) => (p ? `https://erp.lamsa.ly${p}` : null));

describe("meta feed", () => {
  it("builds absolute links and variant grouping", () => {
    expect(rows[0].link).toBe("https://lamsa.ly/p/evening-dress");
    expect(rows[0].image_link).toBe("https://erp.lamsa.ly/files/a.jpg");
    expect(rows[0].additional_image_link).toBe("https://erp.lamsa.ly/files/b.jpg,https://erp.lamsa.ly/files/c.jpg");
    expect(rows[0].item_group_id).toBe("DRESS");
  });

  it("escapes CSV correctly", () => {
    const csv = toCsv(rows);
    expect(csv.startsWith("﻿" + META_COLUMNS.join(","))).toBe(true);
    expect(csv).toContain('"Dress ""Evening"", embroidered"');
    expect(csv).toContain('"Line1\nLine2 & <more>"');
  });

  it("produces escaped RSS 2.0 with the g: namespace", () => {
    const xml = toRssXml(rows, { title: "Lamsa", link: "https://lamsa.ly", description: "d" });
    expect(xml).toContain('xmlns:g="http://base.google.com/ns/1.0"');
    expect(xml).toContain("<g:id>DRESS-M-BGE</g:id>");
    expect(xml).toContain("Line2 &amp; &lt;more&gt;");
    expect(xml.match(/<g:additional_image_link>/g)?.length).toBe(2);
  });
});
