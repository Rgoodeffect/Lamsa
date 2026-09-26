# Lamsa (لمسة): Arabic e-commerce on ERPNext v16 + Next.js

An online store for accessories, gifts, women's and kids' clothing, built for Libya: LYD, Libyan
mobile numbers, Arabic RTL, mobile first, cash on delivery.

- **`store_core/`** is a Frappe v16 app and the single source of truth. Products, stock, prices,
  customers, orders, delivery and accounting all live in ERPNext. It exposes a versioned API at
  `/api/method/store_core.api.v1.*`.
- **`storefront/`** is a Next.js 16 app (App Router, TypeScript, Tailwind v4). It talks to ERPNext
  only from the server with an API key; the browser never sees ERPNext credentials.

```
 Browser ──HTTPS──► nginx ──► Next.js storefront (127.0.0.1:3000)
                                   │  server-only fetch, token auth, X-Lamsa-Client-IP
                                   ▼
                    ERPNext + store_core (gunicorn 127.0.0.1:8000)
                                   │  on Item / Price / Stock change
                                   └──► POST /api/revalidate (ISR refresh)
```

## Contents

1. [Repository layout](#repository-layout)
2. [How an order flows](#how-an-order-flows)
3. [Backend setup (ERPNext)](#backend-setup-erpnext)
4. [Storefront setup](#storefront-setup)
5. [Deployment on the same VPS](#deployment-on-the-same-vps)
6. [Catalog data in ERPNext](#catalog-data-in-erpnext)
7. [Marketing: Meta Pixel, Conversions API, product feed](#marketing-meta-pixel-conversions-api-product-feed)
8. [Payments](#payments)
9. [Adding a payment provider](#adding-a-payment-provider)
10. [Adding a shipping provider or notification channel](#adding-a-shipping-provider-or-notification-channel)
11. [Testing](#testing)
12. [Security notes](#security-notes)
13. [Known limitations and next steps](#known-limitations-and-next-steps)
14. [دليل التشغيل اليومي (عربي)](#دليل-التشغيل-اليومي)

## Repository layout

```
.
├── pyproject.toml              Frappe app package (the repo root is the app, so `bench get-app` works)
├── .env.example                Backend secrets (env or site_config)
├── deploy/                     PM2 + nginx examples
├── store_core/
│   ├── hooks.py                doc_events, provider registries, install hooks
│   ├── api/v1/                 catalog, cart, checkout, orders, payments, store, feeds, agent
│   ├── services/               catalog index, pricing (catalog discounts), orders
│   │                           (quote/checkout/track), payments (online), customer,
│   │                           delivery_flow, feed, events, revalidate
│   ├── providers/              payments / shipping / notifications (interface + registry)
│   ├── integrations/meta/      Conversions API
│   ├── lamsa_store/doctype/    Lamsa Settings, Delivery Zone, Delivery Agent, Delivery
│   │                           Assignment, COD Settlement, Size Guide, Age Range
│   ├── lamsa_store/print_format/lamsa_delivery_note/
│   ├── setup/                  custom fields, install/bootstrap, read-only inspect report
│   ├── www/agent/              mobile page for delivery agents (/agent)
│   ├── locale/ar.po            Arabic desk translations
│   └── tests/                  integration tests + tests/unit (pure Python)
└── storefront/
    ├── messages/ar.json        every customer-facing string
    ├── src/app/globals.css     brand design tokens (@theme)
    ├── src/lib/erp/            server-only ERPNext client, types, mock mode
    ├── src/app/                pages, API routes, feeds, sitemap, robots
    └── tests/                  vitest unit tests + Playwright e2e
```

## How an order flows

| Step | Where | What happens in ERPNext |
|---|---|---|
| Cart / quote | storefront → `cart.quote` | An unsaved Sales Order is built with ERPNext's own pricing (price list, pricing rules, discounts). The gift-wrap fee is the gift-wrap item's price and the delivery fee comes from the Delivery Zone. Nothing is saved. |
| Checkout | `checkout.place_order` | Validates the phone, zone and stock (Bin rows are locked). Matches the Customer by normalized phone or creates Customer + Contact + Address. Creates a **Draft Sales Order** (`L-00001` store number) and a **Delivery Assignment** (`New`). Idempotent per `event_id`. |
| Paid online (card) | gateway callback → `payments.moamalat_callback` | The SecureHash and the amount are verified, the Sales Order is **submitted** and an advance **Payment Entry** is created. The delivery agent then has nothing to collect. |
| Confirm (staff calls the customer) | Delivery Assignment → `Confirmed` | Sales Order is **submitted**, which reserves the stock |
| Hand to agent | → `Out for Delivery` (agent required) | **Delivery Note** created and submitted; stock leaves the warehouse |
| Delivered | agent page or desk → `Delivered` | **Sales Invoice** created and submitted; `collected_amount` recorded; cash counted in the agent's *Cash In Hand* |
| Returned | → `Returned` | Return Delivery Note (stock comes back), Sales Order closed |
| Cancelled | from `New`/`Confirmed` | A submitted Sales Order is cancelled; a draft one is kept and marked `Cancelled` |
| Cash handed in | **COD Settlement** (submit) | One **Payment Entry** per invoice into the COD cash account; cancelling it reverses them |

Draft orders don't reserve stock in ERPNext, so the storefront subtracts quantities held by
unconfirmed store orders when it calculates availability. This prevents overselling while orders
wait for confirmation.

## Backend setup (ERPNext)

Requirements: Frappe/ERPNext **v16** (Python 3.14, Node 24, MariaDB 10.6+, Redis).

```bash
cd ~/frappe-bench
bench get-app https://github.com/rgoodeffect/lamsa      # the app is named store_core
bench --site <site> install-app store_core               # adds lamsa_* custom fields + 3 roles, nothing else
bench --site <site> migrate
bench compile-po-to-mo --app store_core --locale ar      # Arabic desk/agent-page labels
bench build --app store_core
bench restart
```

1. **Check the site first.** This command only reads data:
   ```bash
   bench --site <site> execute store_core.setup.inspect.report
   ```
   It lists apps, companies (should be LYD), price lists, warehouses, item attributes (Size/Color),
   item groups and settings, and prints warnings.
2. **Create the store's master data.** This is explicit on purpose; nothing is created at
   install time. It is idempotent:
   ```bash
   bench --site <site> execute store_core.setup.install.bootstrap \
     --kwargs "{'company': 'Lamsa', 'warehouse': 'Stores - L', 'price_list': 'Standard Selling'}"
   ```
   It creates two non-stock service items (`LAMSA-GIFT-WRAP`, `LAMSA-DELIVERY`), fills
   **Lamsa Settings** with defaults, and creates the API user `storefront-api@lamsa.local` (role
   *Lamsa Storefront API*, no desk access). It **prints the API key and secret once**; put them
   in `storefront/.env.production`.
3. Open **Lamsa Settings** and review: company, price list, store warehouse, customer group and
   territory, Size/Color attribute names, WhatsApp number, COD cash account, enabled payment
   providers (`cod`).
4. Set the gift-wrap fee as the **Item Price** of `LAMSA-GIFT-WRAP` in the store price list.
5. Add **Delivery Zones** (city, area, fee, estimated days), for example طرابلس / حي الأندلس / 15.
6. Add **Delivery Agents**. Each agent needs a User with the role *Lamsa Delivery Agent* and
   language Arabic. Agents log in at `https://<erp-domain>/agent`.
7. Secrets: see `.env.example`. For example:
   ```bash
   bench --site <site> set-config lamsa_revalidate_url http://127.0.0.1:3000/api/revalidate
   bench --site <site> set-config lamsa_revalidate_secret "$(openssl rand -hex 32)"
   ```

Roles: **Lamsa Store Manager** (desk: settings, zones, agents, assignments, settlements),
**Lamsa Delivery Agent** (agent page only) and **Lamsa Storefront API** (API user only).

## Storefront setup

Requirements: Node 20.9+ (Node 24 is already on the VPS for ERPNext v16).

```bash
cd storefront
cp .env.example .env.local      # dev; use .env.production on the server
npm ci
npm run dev                     # http://localhost:3000
```

Set `ERP_MOCK=1` to run without ERPNext. It uses a sample catalog and keeps orders in memory,
which is useful for design work and e2e tests.

Key variables (full list in `storefront/.env.example`):

| Variable | Purpose |
|---|---|
| `ERP_BASE_URL` | `http://127.0.0.1:8000` on the same VPS (gunicorn) |
| `ERP_SITE_NAME` | Frappe site name, sent as `X-Frappe-Site-Name` |
| `ERP_API_KEY` / `ERP_API_SECRET` | from `bootstrap`; server-only |
| `NEXT_PUBLIC_SITE_URL` | public storefront URL (canonical, sitemap, OG, feeds) |
| `NEXT_PUBLIC_ERP_PUBLIC_URL` | public ERPNext URL that serves `/files/*` product images |
| `REVALIDATE_SECRET` | same value as `lamsa_revalidate_secret` |
| `NEXT_PUBLIC_META_PIXEL_ID` | Meta Pixel (optional) |
| `REDIS_URL` | Redis for rate limiting, shared by every Next.js process (optional) |

**Brand:** all colours, fonts and radii are in `storefront/src/app/globals.css` (`@theme`), and the
fonts are chosen in `src/lib/fonts.ts` (El Messiri for headings, IBM Plex Sans Arabic for body).
**Text:** every customer-facing string is in `storefront/messages/ar.json`, and a unit test fails
if Arabic text is hard-coded in `src/`.

## Deployment on the same VPS

```bash
cd ~/lamsa/storefront                  # a clone of this repo (or apps/store_core/storefront)
cp .env.example .env.production && nano .env.production
npm ci && npm run build
npm i -g pm2
pm2 start ../deploy/ecosystem.config.cjs && pm2 save && pm2 startup
sudo cp ../deploy/nginx-lamsa.conf /etc/nginx/conf.d/lamsa.conf    # edit the domain
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d lamsa.ly -d www.lamsa.ly
```

- Catalog pages use ISR (5 minutes), and ERPNext triggers an immediate refresh through
  `/api/revalidate` when items, prices, groups or stock change. That call is debounced in a
  background job, so **the bench workers must be running** (they are in production setups).
- `/checkout` renders per request and the category pages render on demand. Their ERPNext data is
  still cached, so a slow or unreachable ERPNext never breaks `npm run build`.
- Updating: `git pull && npm ci && npm run build && pm2 reload lamsa-storefront`. For the backend:
  `bench update --apps store_core` or `git pull` in `apps/store_core`, then `bench migrate`.

## Running the store (the desk screen)

There is no separate admin app: the shop is run from **ERPNext's own desk**, and store_core adds a
**Lamsa Store** workspace as the landing screen for it. Everything the owner needs is one click from
there — orders, the catalog, prices and offers, delivery setup, and the cash side.

| Task | Where |
|---|---|
| New orders, confirm, dispatch, deliver | **Delivery Assignment** |
| Add a product, publish it in the store | **Item** → *Lamsa* tab → *Publish in Store* |
| Categories | **Item Group** → *Lamsa* tab → *Show in Store* |
| Prices | **Item Price** in the store's price list |
| Discounts and offers | **Pricing Rule** (they show up in `/offers` on the storefront) |
| Sizes and colours | **Item Variant** + **Item Attribute** |
| Delivery zones and fees, agents | **Delivery Zone**, **Delivery Agent** |
| Store settings, coupons | **Lamsa Settings** |
| Cash from agents | **COD Settlement** |

**Give the owner the right roles.** `Lamsa Store Manager` on its own only covers store_core's own
DocTypes; the catalog lives in standard ERPNext DocTypes whose permissions belong to standard roles
(Item needs *Item Manager*, Item Price needs *Sales Master Manager*, Pricing Rule needs
*Sales Manager*). Install creates a **Role Profile** named *Lamsa Store Manager* that bundles all of
them — set it in the **Role Profile** field on the User and nothing else needs ticking. store_core
deliberately does not add Custom DocPerms to core DocTypes, because that would replace their standard
permissions for every other user on the site.

## Catalog data in ERPNext

- **Categories** are Item Groups. In their *Lamsa* tab, tick *Show in Store* and optionally set
  an Arabic title, slug, sort order, *Size Guide* and *Enable Age Range Filter* (kids). A
  sub-group inherits its parent's size guide.
- **Products**: in the Item's *Lamsa* tab, tick *Publish in Store* on the **template** (or on a
  simple item). Clothing uses Item Variants with the Size and Color attributes.
  - ERPNext v16 does **not allow an Item Price on a template**, so give **each variant** a price.
  - Colour swatches go in *Item Attribute → values → Store Swatch* (a colour picker). Keep the
    *Abbreviation* short (`PNK`), because ERPNext puts it in variant item codes.
  - Images: the Item image plus any public image attachments (the first one is the main image).
    Variant images are used when that variant is selected.
  - Kids: set *Age Range* on the template.
- The slug (URL) is generated from the item name (Arabic is fine) and can be edited.
- **Offers**: every discounted product also appears on the storefront's `/offers` page, linked from the
  header, the mobile menu and the footer.
- **Discounts**: a selling **Pricing Rule** shows up on category and product pages as a struck-through
  price plus a “خصم N%” badge, and in the Meta feed as `sale_price`. Only rules a guest is certain to
  get are shown — no coupon, no quantity break, no other customer group, not cumulative or
  mixed-condition — and only the best-priority one per item. Anything else simply shows the
  price-list price. So the catalog can under-advertise a discount but never promises one the cart
  will not honour; the cart total, which runs ERPNext's own pricing engine, is what counts
  (`store_core/services/pricing.py`).

## Marketing: Meta Pixel, Conversions API, product feed

- **Pixel**: set `NEXT_PUBLIC_META_PIXEL_ID`. The storefront sends `PageView`, `ViewContent`,
  `AddToCart`, `InitiateCheckout` and `Purchase`.
- **Conversions API**: set `META_PIXEL_ID` and `META_CAPI_ACCESS_TOKEN` on the ERPNext side. Each
  order sends a server-side `Purchase` with the **same `event_id`** as the browser event, so Meta
  counts it once (`store_core/integrations/meta/capi.py`). It runs in a background job.
- **Product feed** for Commerce Manager → Catalog → Data sources → Scheduled feed:
  - `https://<store>/feeds/meta.csv` or `https://<store>/feeds/meta.xml` (RSS 2.0 with `g:`)
  - There is one row per variant, grouped by `item_group_id`, with `size`, `color`, the price in
    LYD, availability, link, image and additional images. Items without an image are skipped
    because Meta rejects them.

## Search by image

A shopper uploads or pastes a photo and the store shows the products that look like it. It runs
**on the store's own server**: the photo is encoded in the bench process and discarded, never stored
and never sent to a third party.

Setup (it is off until all three are done):

```bash
./env/bin/pip install onnxruntime pillow
# the CLIP *vision* encoder as ONNX — only the image half is needed, roughly half the download
bench --site <site> set-config lamsa_image_model_path /home/frappe/models/clip-vision.onnx
bench --site <site> set-config lamsa_image_model_name clip-vit-b-32-vision
```

Then tick **Lamsa Settings → Search by Image → Enable Search by Image** and build the index once:

```bash
bench --site <site> execute store_core.services.image_search.reindex_all
```

After that it keeps itself current: saving a published Item queues a re-encode of its images in a
background job, so **the bench workers must be running**.

How it works:

- Every product image is encoded once into a unit vector, stored as a **Lamsa Image Embedding** row
  with the name of the model that produced it. Vectors from different models are never compared.
- A search encodes the photo and ranks the stored vectors by cosine similarity. A product is scored by
  its **closest** image, so a photo of the back of a dress still finds it.
- Anything below **Minimum Similarity** (default 0.75) is left out rather than padded in, so an
  unrelated photo honestly returns nothing instead of a random dress.
- The ONNX input and output names are read from the model file at load time, because they differ
  between exports; CLIP's preprocessing (bicubic resize to 224, centre crop, its own channel mean and
  standard deviation) is fixed in `providers/embeddings/clip_onnx.py`. Getting preprocessing wrong does
  not raise — it quietly ruins the matches — so it is written out explicitly there.
- Limits: 8 MB per upload, 10 searches per 5 minutes per shopper IP in Next.js and 20 per 5 minutes in
  ERPNext. Encoding an image costs real CPU on the same box as ERPNext, which is why this is the
  tightest limit in the store.
- A different embedder can be registered with the `lamsa_image_embedders` hook, the same way payment
  and shipping providers are.

The ranking rules are pure Python in `services/vectors.py` and unit tested in
`store_core/tests/unit/test_vectors.py`, so what a customer notices — which product comes first, being
found from any photo of it, and an honest "nothing matched" — is covered without a model or a bench.

## Payments

**Cash on delivery** is the default and needs no configuration: the agent collects the cash and a
COD Settlement books it at the end of the day.

**Moamalat (cards)** is implemented against the published
[Lightbox contract](https://docs.moamalat.net/lightBox.html):

1. Secrets on the ERPNext side (environment or `site_config.json`, never a DocType):
   ```bash
   bench --site <site> set-config moamalat_merchant_id "<MID>"
   bench --site <site> set-config moamalat_terminal_id "<TID>"
   bench --site <site> set-config moamalat_secret_key "<hex secret>"
   bench --site <site> set-config moamalat_env test        # then "live"
   ```
2. In **Lamsa Settings**: set **Online Payment Account** (the account the money is booked into) and
   add `moamalat` to **Enabled Payment Providers**.
3. The checkout then offers the card option. ERPNext builds and signs the Lightbox parameters, the
   customer enters their card inside Moamalat's own iframe, and the widget's result goes back through
   `/api/payment/moamalat`.

What protects the money: an order is only marked paid from a callback whose **SecureHash recomputes**
with the merchant secret (compared in constant time) **and** whose amount equals the order total, so
a customer cannot forge a paid result. Card data never reaches Lamsa. Booking is idempotent per
gateway reference, because the widget can fire its callback more than once, and a failed or abandoned
attempt just leaves the Draft order for the customer to retry. A paid order has
`expected_amount = 0`, so the agent is not told to collect anything.

Check the amount handling before going live: LYD has 3 decimals, so the gateway is sent *dirham*
(1 LYD = 1000). That conversion and the hash are in
`store_core/providers/payments/moamalat_hash.py`, unit tested in
`store_core/tests/unit/test_moamalat.py`.

**Sadad (wallet)** is still a stub: its merchant API is not published, so the three gateway calls are
left to whoever holds the credentials. Everything that is not gateway-specific — submitting the
order, booking the money, idempotency — is already shared with Moamalat in `services/payments.py`.
See `store_core/providers/payments/sadad.py`.

## Loyalty coupons

A delivered order over a set total earns the customer a single-use coupon for their next order.

Turn it on in **Lamsa Settings → Loyalty Coupons**: tick *Reward a Coupon on Delivered Orders*, then
set *Order Total to Earn a Coupon*, *Coupon Discount %* and *Coupon Valid For (days)*.

- The coupon is an ERPNext **Coupon Code** (type *Gift Card*: single use, bound to that customer), so
  ERPNext owns its lifecycle — `Sales Order.validate` checks the dates and usage, `on_submit` and
  `on_cancel` move the `used` counter. A coupon cannot be spent twice, and a cancelled order releases
  it again.
- The discount is a percentage of the **goods only**: delivery and gift wrap are passed through at
  cost.
- It is earned on **Delivered**, not at checkout, so a cancelled order cannot mint one; and at most
  one coupon per order however often a status change is replayed. The code is sent with the order
  notification (`coupon_earned`).
- Each coupon keeps its own percentage (`Coupon Code → Store Discount %`), so changing the setting
  later never re-prices a coupon a customer is already holding.
- Shoppers enter it in the cart or at checkout; the amount comes back from the server quote, so the
  browser cannot change what is charged.

Note on implementation: this is *not* a coupon-based Pricing Rule. Transaction-level pricing rules are
applied by ERPNext's client-side code and never on a server-side save, so the cart quote and the order
— both built by `services.orders.build_sales_order` — would have ignored one. The discount is the
Sales Order's own `discount_amount`, which is core arithmetic in `calculate_taxes_and_totals`.

## Adding a payment provider

1. Create a class implementing `store_core.providers.payments.base.PaymentProvider`:

   ```python
   # my_app/payments/tadawul.py
   from store_core.providers.payments.base import PaymentProvider, PaymentResult
   from store_core.services.settings import get_secret

   class TadawulPay(PaymentProvider):
       label_key = "payment.tadawul"      # add this key to storefront/messages/ar.json
       is_online = True

       def initiate(self, sales_order) -> PaymentResult:
           api_key = get_secret("tadawul_api_key")   # env or site_config, never a DocType
           session = ...                             # call the gateway
           return PaymentResult(status="redirect", provider=self.code, redirect_url=session.url,
                                reference=session.id, amount=sales_order.grand_total)

       def verify(self, payload: dict) -> PaymentResult:
           ...  # check the signature (hmac.compare_digest), amount and order no
   ```
2. Register it in **any** app's `hooks.py` (store_core itself doesn't need to change):
   ```python
   lamsa_payment_providers = ["tadawul:my_app.payments.tadawul.TadawulPay"]
   ```
3. Add a guest, rate-limited callback endpoint that calls `verify()`, then submits the Sales Order
   and records a Payment Entry (`erpnext...payment_entry.get_payment_entry("Sales Order", name)`).
   Make it idempotent, because gateways retry. `moamalat.py` has a step-by-step checklist.
4. Enable it: add `tadawul` to *Lamsa Settings → Enabled Payment Providers*. The checkout page
   lists it automatically. When `initiate()` returns `redirect`, the storefront sends the customer
   to `redirect_url`.

Stubs with documentation are included for **Moamalat** (cards) and **Sadad** (wallet OTP).

## Adding a shipping provider or notification channel

- **Shipping**: implement `ShippingProvider` (`create_shipment`, `get_label`, `track`) and
  register it with `lamsa_shipping_providers = ["aramex:my_app.shipping.Aramex"]`, then select
  it in *Lamsa Settings → Shipping Provider*. `create_shipment` is called when an order goes
  *Out for Delivery*, and the reference is saved on the Delivery Assignment. `manual` (own agents)
  is the default.
- **Notifications**: implement `NotificationChannel.send(message)` and register it with
  `lamsa_notification_channels`. Order status messages (`providers/notifications/templates.py`)
  are sent in background jobs, and a failure never blocks a status change. The default `log`
  channel writes the message as a comment on the Sales Order.
- **WhatsApp** is implemented against the WhatsApp Business Cloud API. Set `WHATSAPP_TOKEN` and
  `WHATSAPP_PHONE_NUMBER_ID` (and optionally `WHATSAPP_API_VERSION`), then select `whatsapp` as
  *Lamsa Settings → Order Notification Channel*. Business-initiated messages must use approved
  templates, so register one per key of `providers/notifications/templates.py` in Meta Business
  Manager, language `ar`, with that key's text and its placeholders as `{{1}}, {{2}}, ...`
  **in the order they appear in the text** — `templates_params.placeholders()` derives that order
  from the text itself, so the two cannot drift apart. Until the credentials are set, the channel
  falls back to writing the message on the order, and a failed send is logged and also written
  there, so nothing is lost. `WHATSAPP_FREE_TEXT=1` sends plain text instead of a template, which
  Meta only delivers inside the 24-hour window — for testing, not production.

## Testing

```bash
# Backend, pure unit tests (no bench needed): phone, slug, status machine, message templates
# and the Moamalat SecureHash
python -m pytest store_core/tests/unit

# Backend integration tests on a dev/test site (never production)
bench --site test.local set-config allow_tests true
bench --site test.local run-tests --app store_core

# Storefront
cd storefront
npm run lint && npm run typecheck && npm test
npm run e2e          # Playwright, builds and runs in ERP_MOCK mode

# The card payment UI, against a fake gateway (no merchant account needed)
ERP_MOCK=1 ERP_MOCK_ONLINE_PAYMENT=1 npm run dev
```

The integration tests run as a user holding **only** the storefront API role, like production.
They cover quote pricing, checkout, idempotency, draft stock holding, validation, tracking, the
full COD cycle (confirm → dispatch → deliver → settle → cancel settlement), returns, cancellations,
agent permissions and the Meta feed.

## Security notes

- ERPNext endpoints reject guests. Only the storefront API user (or a System Manager) can call
  them, so the public surface is the storefront's own `/api/*` routes.
- Rate limiting has two layers. Next.js limits per shopper IP (checkout 5 per 10 minutes,
  tracking 10 per 5 minutes, quote 60 per minute, payment callbacks 20 per 10 minutes), backed by
  Redis when `REDIS_URL` is set so every process shares the count, and ERPNext enforces its own
  Redis-backed limits per forwarded IP.
- Tracking returns the same error for an unknown order and a wrong phone, and compares phones in
  constant time.
- Prices, discounts, stock, gift-wrap and delivery fees are computed only on the server. The cart
  sends item codes and quantities only.
- An online payment is only ever booked from a gateway response whose signature recomputes with the
  merchant secret (constant-time compare) and whose amount equals the order total, so the browser
  that carries the response cannot change the outcome. Booking is idempotent per gateway reference.
- Payment status can be read with the order number *and* the checkout's `event_id`, which only the
  browser that placed the order has, so an order number alone reveals nothing.
- ERPNext's pricing code checks Item permissions for the session user. Quote and checkout
  therefore run it in a short, scoped system context (`services/orders.system_context`), but only
  after the endpoint has verified the storefront role and validated the input. This avoids
  granting the API role permissions on core DocTypes.
- Secrets are read from environment variables or `site_config.json`, never from DocTypes. That
  includes the merchant keys (`MOAMALAT_SECRET_KEY`) and the WhatsApp token.
- Product descriptions (HTML from ERPNext) are sanitized again in the storefront before rendering.

## Known limitations and next steps

- **Moamalat** is implemented but has only been exercised against its published contract and unit
  tests; run a test-environment transaction end to end (and check the amount, in dirham, on the
  merchant portal) before switching `MOAMALAT_ENV` to `live`.
- **Sadad** and carrier integrations are still documented stubs: their APIs are not published.
- Catalog pages show discounts from unconditional Pricing Rules only; see
  [Catalog data in ERPNext](#catalog-data-in-erpnext).
- A delivered order cannot be returned through the store flow (`Delivered` is final); do those in
  ERPNext directly, as a Sales Return against the invoice.
- The catalog index is cached in Redis and rebuilt on change. It suits catalogs up to a few
  thousand templates; beyond that, move it into a table or a search engine.
- Image search compares the query against every stored vector on each search. That is fine for a few
  thousand images; beyond that, put the vectors in a vector index. The model also holds a few hundred
  megabytes of memory in whichever worker last used it — check the VPS has room before enabling it
  alongside ERPNext, MariaDB, Redis and Next.js.
- The first rate-limit layer uses Redis when `REDIS_URL` is set, so several Next.js processes share
  it. Without Redis — or while Redis is unreachable — it falls back to per-process in-memory
  limiting, which loosens the limit but never closes the store.

## دليل التشغيل اليومي

1. **طلب جديد** يظهر في *Delivery Assignment* بحالة «جديد»، ومعه أمر بيع **مسودة**.
2. **اتصلي بالزبونة** لتأكيد الطلب، ثم اضغطي *Set Status → Confirmed*، فيُعتمد أمر البيع ويُحجز المخزون.
3. **جهّزي الطلب** واطبعي *Lamsa Delivery Note*، وستظهر فيه رسالة الهدية والمبلغ المطلوب تحصيله.
4. **اختاري المندوب** واضغطي *Out for Delivery*، فيُنشأ إذن التسليم ويخرج المخزون.
5. **المندوب** يفتح `/agent` من جواله ويضغط «تم التسليم واستلام المبلغ»، فتُنشأ الفاتورة تلقائياً.
6. **نهاية اليوم**: أنشئي *COD Settlement* للمندوب، واضغطي *Get Unsettled Orders*، ثم *Submit*. تُسجَّل دفعات الفواتير في الصندوق ويصبح «النقد لدى المندوب» صفراً.
7. **الإرجاع**: اضغطي *Returned*، فيعود المخزون ويُغلق أمر البيع.

### الطلبات المدفوعة بالبطاقة

إذا فُعّلت بوابة «معاملات»:

- الطلب المدفوع يصل وقد **اعتُمد أمر البيع** وسُجّلت الدفعة، وتكون خانة *Amount to Collect* **صفراً**،
  فلا يُطلب من المندوب تحصيل أي مبلغ. تحقّقي من حقل *Payment Status* في أمر البيع (**Paid**).
- إن أظهر الطلب *Payment Status* فارغاً أو **Unpaid** فالزبونة لم تُكمل الدفع؛ تعامَلي معه كطلب عادي
  واتصلي بها، أو اقترحي الدفع عند الاستلام.
- **قبل التشغيل الفعلي**: نفّذي عملية تجريبية كاملة على البيئة التجريبية (`MOAMALAT_ENV=test`) وتأكّدي
  من صحة المبلغ في لوحة التاجر، لأن الدينار الليبي يُرسل بالدرهم (١ د.ل = ١٠٠٠).

### الخصومات

لإظهار خصم على صفحات المتجر أنشئي *Pricing Rule* للبيع على الصنف أو المجموعة أو الماركة، دون كوبون
ودون شرط كمية ودون تخصيص لزبونة معيّنة. يظهر السعر القديم مشطوباً مع شارة «خصم N%»، ويصل الخصم إلى
كتالوج Meta في حقل `sale_price`. أي قاعدة مشروطة تُطبَّق في السلة فقط.
