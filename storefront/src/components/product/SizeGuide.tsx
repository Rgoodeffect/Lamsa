"use client";

import { useRef } from "react";

import type { SizeGuide as Guide } from "@/lib/erp/types";
import { t, tDynamic } from "@/lib/i18n";

import { CloseIcon } from "../Icons";

export function SizeGuideButton({ guide }: { guide: Guide }) {
  const ref = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button type="button" className="text-sm font-semibold text-primary-700 underline underline-offset-4" onClick={() => ref.current?.showModal()}>
        {t("product.size_guide")}
      </button>
      <dialog ref={ref} className="m-auto w-[min(36rem,92vw)] rounded-card p-0 backdrop:bg-ink/40" aria-label={guide.title}>
        <div className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-heading text-xl font-bold">{guide.title}</h2>
            <button className="rounded-full p-2 hover:bg-primary-50" aria-label={t("nav.close")} onClick={() => ref.current?.close()}>
              <CloseIcon />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-center text-sm">
              <thead>
                <tr className="bg-primary-50">
                  {guide.columns.map((c) => (
                    <th key={c} className="px-3 py-2 font-semibold">
                      {tDynamic(`size_guide.${c}`, "product.size_guide")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {guide.rows.map((row, i) => (
                  <tr key={i} className="border-b border-line">
                    {guide.columns.map((c) => (
                      <td key={c} className="px-3 py-2">
                        {row[c] ?? "-"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {guide.notes && <p className="mt-3 text-xs text-muted">{guide.notes}</p>}
        </div>
      </dialog>
    </>
  );
}
