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
8. [Adding a payment provider](#adding-a-payment-provider)
9. [Adding a shipping provider or notification channel](#adding-a-shipping-provider-or-notification-channel)
10. [Testing](#testing)
11. [Security notes](#security-notes)
12. [Known limitations and next steps](#known-limitations-and-next-steps)
13. [دليل التشغيل اليومي (عربي)](#دليل-التشغيل-اليومي)

## Repository layout

```
.
├── pyproject.toml              Frappe app package (the repo root is the app, so `bench get-app` works)
├── .env.example                Backend secrets (env or site_config)
├── deploy/                     PM2 + nginx examples
├── store_core/
│   ├── hooks.py                doc_events, provider registries, install hooks
│   ├── api/v1/                 catalog, cart, checkout, orders, store, feeds, agent
│   ├── services/               catalog index, orders (quote/checkout/track), customer,
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
  channel writes the message as a comment on the Sales Order. `whatsapp` is a documented stub for
  the WhatsApp Business Cloud API: register the same template names in Meta.

## Testing

```bash
# Backend, pure unit tests (no bench needed)
python -m pytest store_core/tests/unit

# Backend integration tests on a dev/test site (never production)
bench --site test.local set-config allow_tests true
bench --site test.local run-tests --app store_core

# Storefront
cd storefront
npm run lint && npm run typecheck && npm test
npm run e2e          # Playwright, builds and runs in ERP_MOCK mode
```

The integration tests run as a user holding **only** the storefront API role, like production.
They cover quote pricing, checkout, idempotency, draft stock holding, validation, tracking, the
full COD cycle (confirm → dispatch → deliver → settle → cancel settlement), returns, cancellations,
agent permissions and the Meta feed.

## Security notes

- ERPNext endpoints reject guests. Only the storefront API user (or a System Manager) can call
  them, so the public surface is the storefront's own `/api/*` routes.
- Rate limiting has two layers. Next.js limits per shopper IP (checkout 5 per 10 minutes,
  tracking 10 per 5 minutes, quote 60 per minute), and ERPNext enforces its own Redis-backed
  limits per forwarded IP.
- Tracking returns the same error for an unknown order and a wrong phone, and compares phones in
  constant time.
- Prices, discounts, stock, gift-wrap and delivery fees are computed only on the server. The cart
  sends item codes and quantities only.
- ERPNext's pricing code checks Item permissions for the session user. Quote and checkout
  therefore run it in a short, scoped system context (`services/orders.system_context`), but only
  after the endpoint has verified the storefront role and validated the input. This avoids
  granting the API role permissions on core DocTypes.
- Secrets are read from environment variables or `site_config.json`, never from DocTypes.
- Product descriptions (HTML from ERPNext) are sanitized again in the storefront before rendering.

## Known limitations and next steps

- Payment gateways (Moamalat, Sadad), WhatsApp sending and carrier integrations are documented
  stubs, by design for Phase 1.
- Pricing Rule discounts are applied in the cart/checkout quote. Catalog pages show the price-list
  price.
- The catalog index is cached in Redis and rebuilt on change. It suits catalogs up to a few
  thousand templates; beyond that, move it into a table or a search engine.
- The first rate-limit layer is per Next.js process. Keep PM2 at one instance, or move that
  layer to Redis before scaling out.

## دليل التشغيل اليومي

1. **طلب جديد** يظهر في *Delivery Assignment* بحالة «جديد»، ومعه أمر بيع **مسودة**.
2. **اتصلي بالزبونة** لتأكيد الطلب، ثم اضغطي *Set Status → Confirmed*، فيُعتمد أمر البيع ويُحجز المخزون.
3. **جهّزي الطلب** واطبعي *Lamsa Delivery Note*، وستظهر فيه رسالة الهدية والمبلغ المطلوب تحصيله.
4. **اختاري المندوب** واضغطي *Out for Delivery*، فيُنشأ إذن التسليم ويخرج المخزون.
5. **المندوب** يفتح `/agent` من جواله ويضغط «تم التسليم واستلام المبلغ»، فتُنشأ الفاتورة تلقائياً.
6. **نهاية اليوم**: أنشئي *COD Settlement* للمندوب، واضغطي *Get Unsettled Orders*، ثم *Submit*. تُسجَّل دفعات الفواتير في الصندوق ويصبح «النقد لدى المندوب» صفراً.
7. **الإرجاع**: اضغطي *Returned*، فيعود المخزون ويُغلق أمر البيع.
