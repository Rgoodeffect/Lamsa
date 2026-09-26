import type { NextConfig } from "next";

const erpPublicUrl = process.env.NEXT_PUBLIC_ERP_PUBLIC_URL;

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // The e2e suite builds and serves its own copy; giving it a separate directory keeps that build
  // from overwriting the .next a `npm run dev` or `next start` in this folder is serving.
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
  images: {
    // Product images are served by ERPNext under /files/
    remotePatterns: erpPublicUrl ? [new URL(`${erpPublicUrl.replace(/\/$/, "")}/files/**`)] : [],
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
