"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import type { Category } from "@/lib/erp/types";
import { t } from "@/lib/i18n";

import { CloseIcon, MenuIcon } from "../Icons";

export function MobileMenu({ categories }: { categories: Category[] }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // close the drawer after navigation
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <div className="md:hidden">
      <button
        type="button"
        className="rounded-full p-2.5 hover:bg-primary-50"
        aria-label={t("nav.menu")}
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        <MenuIcon />
      </button>
      {open && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={t("nav.menu")}>
          <button className="absolute inset-0 bg-ink/40" aria-label={t("nav.close")} onClick={() => setOpen(false)} />
          <nav className="absolute inset-y-0 start-0 w-[82%] max-w-sm overflow-y-auto bg-cream p-5 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <span className="font-heading text-2xl font-bold text-primary-600">{t("brand.name")}</span>
              <button className="rounded-full p-2 hover:bg-primary-50" aria-label={t("nav.close")} onClick={() => setOpen(false)}>
                <CloseIcon />
              </button>
            </div>
            <ul className="space-y-1">
              {categories.map((c) => (
                <li key={c.slug}>
                  <Link href={`/c/${c.slug}`} className="block rounded-xl px-3 py-3 text-lg font-semibold hover:bg-primary-50">
                    {c.title}
                  </Link>
                  {c.children.length > 0 && (
                    <ul className="ms-4 border-s border-line ps-2">
                      {c.children.map((child) => (
                        <li key={child.slug}>
                          <Link href={`/c/${child.slug}`} className="block rounded-lg px-3 py-2 text-muted hover:text-primary-700">
                            {child.title}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
              <li className="border-t border-line pt-3">
                <Link href="/track" className="block rounded-xl px-3 py-3 hover:bg-primary-50">
                  {t("nav.track")}
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      )}
    </div>
  );
}
