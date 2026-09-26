import { El_Messiri, IBM_Plex_Sans_Arabic } from "next/font/google";

/**
 * Brand fonts. To change them, swap the imports here; globals.css maps
 * --font-lamsa-heading / --font-lamsa-body to Tailwind's font-heading / font-body.
 */
export const headingFont = El_Messiri({
  subsets: ["arabic", "latin"],
  weight: ["500", "600", "700"],
  variable: "--font-lamsa-heading",
  display: "swap",
});

export const bodyFont = IBM_Plex_Sans_Arabic({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-lamsa-body",
  display: "swap",
});
