import type { Metadata, Viewport } from "next";

import { JsonLd } from "@/components/JsonLd";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { MetaPixel } from "@/components/layout/MetaPixel";
import { WhatsAppFab } from "@/components/layout/WhatsAppFab";
import { publicEnv } from "@/lib/env";
import { getCategories, getStoreConfig } from "@/lib/erp";
import { bodyFont, headingFont } from "@/lib/fonts";
import { dir, t } from "@/lib/i18n";
import { organizationJsonLd } from "@/lib/seo/jsonld";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(publicEnv.siteUrl),
  title: { default: `${t("brand.name")} | ${t("brand.tagline")}`, template: `%s | ${t("brand.name")}` },
  description: t("brand.description"),
  applicationName: t("brand.name"),
  openGraph: {
    type: "website",
    locale: "ar_LY",
    siteName: t("brand.name"),
    title: t("brand.name"),
    description: t("brand.description"),
  },
  twitter: { card: "summary_large_image" },
  alternates: { canonical: "/" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#fbf8f4",
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [categories, config] = await Promise.all([getCategories(), getStoreConfig()]);
  const tree = categories.ok ? categories.data.categories : [];
  const whatsapp = (config.ok && config.data.whatsapp) || publicEnv.whatsappNumber || null;

  return (
    <html lang="ar" dir={dir} className={`${headingFont.variable} ${bodyFont.variable}`}>
      <body className="flex min-h-dvh flex-col antialiased">
        <Header categories={tree} />
        <main id="main" className="flex-1">
          {children}
        </main>
        <Footer categories={tree} />
        <WhatsAppFab number={whatsapp} />
        {publicEnv.metaPixelId && <MetaPixel pixelId={publicEnv.metaPixelId} />}
        <JsonLd data={organizationJsonLd()} />
      </body>
    </html>
  );
}
