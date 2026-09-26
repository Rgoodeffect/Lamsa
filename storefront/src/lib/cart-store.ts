"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * The cart only stores what the customer picked. Prices are never stored or trusted here:
 * every display of totals comes from the server quote (/api/quote).
 * `display` is a snapshot for rendering the cart before the quote returns.
 */
export type CartLine = {
  item_code: string;
  qty: number;
  display: { name: string; slug: string; image: string | null; options: string[] };
};

type CartState = {
  lines: CartLine[];
  add: (line: CartLine, maxQty: number) => void;
  setQty: (itemCode: string, qty: number) => void;
  remove: (itemCode: string) => void;
  clear: () => void;
};

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      lines: [],
      add: (line, maxQty) =>
        set((state) => {
          const existing = state.lines.find((l) => l.item_code === line.item_code);
          if (existing) {
            return {
              lines: state.lines.map((l) =>
                l.item_code === line.item_code ? { ...l, qty: Math.min(l.qty + line.qty, maxQty) } : l,
              ),
            };
          }
          return { lines: [...state.lines, { ...line, qty: Math.min(line.qty, maxQty) }] };
        }),
      setQty: (itemCode, qty) =>
        set((state) => ({
          lines: state.lines.map((l) => (l.item_code === itemCode ? { ...l, qty: Math.max(1, qty) } : l)),
        })),
      remove: (itemCode) => set((state) => ({ lines: state.lines.filter((l) => l.item_code !== itemCode) })),
      clear: () => set({ lines: [] }),
    }),
    { name: "lamsa-cart", version: 1, storage: createJSONStorage(() => localStorage) },
  ),
);

export const cartCount = (lines: CartLine[]) => lines.reduce((sum, l) => sum + l.qty, 0);
