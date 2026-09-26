import { defineConfig, devices } from "@playwright/test";

/** e2e runs against a production build in ERP_MOCK mode (no ERPNext needed). */
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  use: { baseURL: "http://localhost:3200", locale: "ar-LY", ...devices["Pixel 7"] },
  webServer: {
    command: "npm run build && npx next start -p 3200",
    url: "http://localhost:3200",
    timeout: 240_000,
    reuseExistingServer: false,
    env: { ERP_MOCK: "1", NEXT_PUBLIC_SITE_URL: "http://localhost:3200", NEXT_PUBLIC_WHATSAPP_NUMBER: "218912345678", RATE_LIMIT_CHECKOUT_PER_10MIN: "50" },
  },
});
