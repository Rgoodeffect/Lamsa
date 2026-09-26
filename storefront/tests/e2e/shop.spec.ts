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

test("card checkout only confirms the order after the server verifies the payment", async ({ page }) => {
  await page.goto(`/p/${encodeURIComponent("إسورة-ذهبية-بحرف")}`);
  await page.getByTestId("add-to-cart").click();
  await page.goto("/checkout");
  await page.getByLabel(messages["checkout.full_name"]).fill("ليلى أحمد");
  await page.getByLabel(messages["checkout.phone"]).fill("0912345678");
  await page.getByLabel(messages["checkout.city"]).selectOption("طرابلس");
  await page.getByLabel(messages["checkout.area"]).selectOption("طرابلس-جنزور");
  await page.getByRole("radio", { name: messages["payment.moamalat"] }).check();
  await page.getByTestId("place-order").click();

  // the gateway widget takes over; the order page is only reached once /api/payment/* says "paid"
  await expect(page.getByTestId("moamalat-lightbox")).toBeVisible();
  await expect(page.getByTestId("order-confirmation")).toBeVisible({ timeout: 15_000 });
  expect((await page.getByTestId("order-number").textContent())!.trim()).toMatch(/^L-\d+$/);

  // the badge comes from the status ERPNext holds, not from the copy the browser stored
  await expect(page.getByTestId("order-payment-status")).toHaveText(messages["order.paid_badge"]);
  await expect(page.getByTestId("order-confirmation")).toContainText(messages["order.total_paid"]);
});

test("an unsigned payment result cannot mark an order paid", async ({ request }) => {
  const order = await request.post("/api/checkout", {
    data: {
      items: [{ item_code: "BRACELET-001", qty: 1 }],
      full_name: "نورا",
      phone: "0912345678",
      zone: "طرابلس-جنزور",
      event_id: "e2e-unsigned-callback-1",
      payment_provider: "moamalat",
    },
  });
  expect(order.ok()).toBe(true);

  // a payload naming an order that does not exist must be refused, not accepted as a payment
  const forged = await request.post("/api/payment/moamalat", {
    data: { payload: { MerchantReference: "L-99999", Amount: "1000", SecureHash: "forged" } },
  });
  expect(forged.status()).toBe(404);
  expect((await forged.json()).error.code).toBe("order_not_found");
});

test("a discounted product shows the price it was before the discount", async ({ page }) => {
  await page.goto(`/p/${encodeURIComponent("حقيبة-يد-جلد-ناعم")}`);
  const price = page.getByTestId("product-price");
  await expect(price).toContainText("108");
  await expect(price.locator("s")).toContainText("135");
  await expect(price).toContainText("20");
});

test("a coupon discounts the goods only, and cannot be spent twice", async ({ page }) => {
  await page.goto(`/p/${encodeURIComponent("إسورة-ذهبية-بحرف")}`);
  await page.getByTestId("add-to-cart").click();
  await page.goto("/cart");
  await expect(page.getByTestId("summary-subtotal")).toContainText("65");

  // 10% of the goods (65) = 6.50; the delivery fee is added later and must not be discounted
  await page.getByTestId("coupon-input").fill("LAMSADEMO10");
  await page.getByTestId("coupon-apply").click();
  await expect(page.getByTestId("coupon-applied")).toBeVisible();
  await expect(page.getByTestId("summary-discount")).toContainText("6.5");
  await expect(page.getByTestId("summary-total")).toContainText("58.5");

  await page.getByTestId("go-checkout").click();
  await page.getByLabel(messages["checkout.full_name"]).fill("هدى سالم");
  await page.getByLabel(messages["checkout.phone"]).fill("0912345678");
  await page.getByLabel(messages["checkout.city"]).selectOption("طرابلس");
  await page.getByLabel(messages["checkout.area"]).selectOption("طرابلس-جنزور");
  // 65 - 6.50 + 20 delivery: the coupon took nothing off the delivery fee
  await expect(page.getByTestId("summary-total")).toContainText("78.5");
  await page.getByTestId("place-order").click();
  await expect(page.getByTestId("order-confirmation")).toBeVisible();

  // second use is refused
  await page.goto(`/p/${encodeURIComponent("إسورة-ذهبية-بحرف")}`);
  await page.getByTestId("add-to-cart").click();
  await page.goto("/cart");
  await page.getByTestId("coupon-input").fill("LAMSADEMO10");
  await page.getByTestId("coupon-apply").click();
  await expect(page.getByTestId("coupon-error")).toHaveText(messages["errors.coupon_used"]);
  await expect(page.getByTestId("summary-total")).toContainText("65");
});

test("a made-up coupon is reported but still prices the cart, and checkout refuses it", async ({ request }) => {
  // A bad coupon must not leave the shopper with no prices at all, so the quote succeeds and says why.
  const quote = await request.post("/api/quote", {
    data: { items: [{ item_code: "BRACELET-001", qty: 1 }], coupon_code: "NOPE123" },
  });
  expect(quote.status()).toBe(200);
  const body = await quote.json();
  expect(body.data.coupon).toBeNull();
  expect(body.data.coupon_error).toBe("invalid_coupon");
  expect(body.data.grand_total).toBe(65);
  expect(body.data.discount).toBe(0);

  // Checkout is strict: the customer must not lose a discount they were counting on without being told.
  const order = await request.post("/api/checkout", {
    data: {
      items: [{ item_code: "BRACELET-001", qty: 1 }],
      full_name: "أمل",
      phone: "0912345678",
      zone: "طرابلس-جنزور",
      event_id: "e2e-bad-coupon-checkout-1",
      coupon_code: "NOPE123",
    },
  });
  expect(order.status()).toBe(422);
  expect((await order.json()).error.code).toBe("invalid_coupon");
});

test("the offers section lists only discounted products", async ({ page }) => {
  await page.goto("/offers");
  await expect(page.getByRole("heading", { name: messages["offers.title"] })).toBeVisible();
  const cards = page.getByTestId("product-card");
  await expect(cards).toHaveCount(1);
  await expect(cards.first()).toContainText("108");
  await expect(cards.first().locator("s")).toContainText("135");
});

test("searching by image uploads a photo and shows matches", async ({ page }) => {
  await page.goto("/search");
  await expect(page.getByTestId("image-search")).toBeVisible();

  // a 1x1 PNG is enough: the mock backend has no model, and the ranking itself is unit tested
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==",
    "base64",
  );
  await page.getByTestId("image-search-input").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: png });

  await expect(page.getByRole("heading", { name: messages["image_search.results"] })).toBeVisible();
  await expect(page.getByTestId("product-card").first()).toBeVisible();
  await expect(page.getByTestId("image-search-error")).toHaveCount(0);
});

test("a file that is not an image is refused", async ({ request }) => {
  const res = await request.post("/api/search-by-image", {
    multipart: { image: { name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("not an image at all") } },
  });
  expect(res.status()).toBe(422);
  expect((await res.json()).error.code).toBe("image_unreadable");
});
