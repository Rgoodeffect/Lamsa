import { expect, test } from "@playwright/test";

import messages from "../../messages/ar.json";

test("browse, add a variant, checkout with gift wrap, confirm and track", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByTestId("whatsapp-fab")).toHaveAttribute("href", /wa\.me\/218912345678/);

  // category + filter
  await page.goto("/c/women?size=XL");
  await expect(page.getByTestId("product-card")).toHaveCount(2);

  // product: choose colour + size
  await page.goto(`/p/${encodeURIComponent("فستان-سهرة-مطرز")}`);
  await expect(page.getByTestId("add-to-cart")).toBeDisabled();
  await page.getByRole("button", { name: "وردي" }).click();
  await page.getByRole("button", { name: "M", exact: true }).click();
  await expect(page.getByTestId("stock-badge")).toHaveText(messages["product.low_stock"].replace("{left}", "2"));
  await page.getByTestId("add-to-cart").click();
  await expect(page.getByTestId("cart-button")).toContainText("1");

  // cart shows server prices
  await page.goto("/cart");
  await expect(page.getByTestId("summary-subtotal")).toContainText("250");

  // checkout
  await page.getByTestId("go-checkout").click();
  await page.getByLabel(messages["checkout.full_name"]).fill("سارة محمد");
  await page.getByLabel(messages["checkout.phone"]).fill("091-234-5678");
  await page.getByLabel(messages["checkout.city"]).selectOption("طرابلس");
  await page.getByLabel(messages["checkout.area"]).selectOption("طرابلس-جنزور");
  await page.getByTestId("gift-wrap").check();
  await page.getByLabel(messages["checkout.gift_message"]).fill("كل عام وأنتِ بخير");
  await expect(page.getByTestId("summary-total")).toContainText("280"); // 250 + 20 delivery + 10 wrap
  await page.getByTestId("place-order").click();

  await expect(page.getByTestId("order-confirmation")).toBeVisible();
  const orderNo = (await page.getByTestId("order-number").textContent())!.trim();
  expect(orderNo).toMatch(/^L-\d+$/);
  await expect(page.getByTestId("cart-button")).not.toContainText("1");

  // tracking needs the matching phone
  await page.goto(`/track?order=${orderNo}`);
  await page.getByLabel(messages["track.phone"]).fill("0922222222");
  await page.getByRole("button", { name: messages["track.submit"] }).click();
  await expect(page.getByText(messages["errors.order_not_found"])).toBeVisible();
  await page.getByLabel(messages["track.phone"]).fill("+218912345678");
  await page.getByRole("button", { name: messages["track.submit"] }).click();
  await expect(page.getByTestId("track-status")).toHaveText(messages["status.New"]);
});

test("checkout validates Libyan phone numbers", async ({ page }) => {
  await page.goto(`/p/${encodeURIComponent("إسورة-ذهبية-بحرف")}`);
  await page.getByTestId("add-to-cart").click();
  await page.goto("/checkout");
  await page.getByLabel(messages["checkout.full_name"]).fill("منى");
  await page.getByLabel(messages["checkout.phone"]).fill("021 333 4444");
  await page.getByTestId("place-order").click();
  await expect(page.getByText(messages["errors.invalid_phone"])).toBeVisible();
});

test("api rejects tampered carts and never trusts client prices", async ({ request }) => {
  const res = await request.post("/api/quote", { data: { items: [{ item_code: "BRACELET-001", qty: 1, rate: 1 }] } });
  const body = await res.json();
  expect(body.data.grand_total).toBe(65);
  const bad = await request.post("/api/quote", { data: { items: [{ item_code: "NOPE", qty: 1 }] } });
  expect(bad.status()).toBe(422);
  expect((await bad.json()).error.code).toBe("item_unavailable");
});
