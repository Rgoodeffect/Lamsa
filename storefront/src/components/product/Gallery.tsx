"use client";

import { useState } from "react";

import { t } from "@/lib/i18n";

import { ProductImage } from "../ProductImage";

export function Gallery({ images, alt }: { images: string[]; alt: string }) {
  const list = images.length ? images : [null];
  const [active, setActive] = useState(0);

  return (
    <div className="space-y-3">
      {/* mobile: swipeable strip; desktop: main image */}
      <div
        className="flex snap-x snap-mandatory overflow-x-auto rounded-card md:block"
        onScroll={(e) => {
          const el = e.currentTarget;
          setActive(Math.round(Math.abs(el.scrollLeft) / el.clientWidth));
        }}
      >
        {list.map((src, i) => (
          <div
            key={src ?? i}
            className={`relative aspect-[4/5] w-full shrink-0 snap-center bg-primary-50 ${i === active ? "md:block" : "md:hidden"}`}
          >
            <ProductImage
              src={src}
              alt={list.length > 1 ? `${alt} - ${t("product.gallery_image", { index: i + 1, total: list.length })}` : alt}
              fill
              priority={i === 0}
              sizes="(min-width: 768px) 50vw, 100vw"
              className="object-cover"
            />
          </div>
        ))}
      </div>
      {list.length > 1 && (
        <div className="hidden gap-2 md:flex">
          {list.map((src, i) => (
            <button
              key={src ?? i}
              type="button"
              onClick={() => setActive(i)}
              aria-label={t("product.gallery_image", { index: i + 1, total: list.length })}
              aria-current={i === active}
              className="relative h-20 w-16 overflow-hidden rounded-xl border-2 border-transparent aria-[current=true]:border-primary-500"
            >
              <ProductImage src={src} alt="" fill sizes="64px" className="object-cover" />
            </button>
          ))}
        </div>
      )}
      {list.length > 1 && (
        <div className="flex justify-center gap-1.5 md:hidden" aria-hidden>
          {list.map((_, i) => (
            <span key={i} className={`h-1.5 rounded-full transition-all ${i === active ? "w-5 bg-primary-500" : "w-1.5 bg-primary-200"}`} />
          ))}
        </div>
      )}
    </div>
  );
}
