import { t } from "@/lib/i18n";
import { whatsappLink } from "@/lib/whatsapp";

import { WhatsAppIcon } from "../Icons";

export function WhatsAppFab({ number }: { number: string | null }) {
  const href = whatsappLink(number, t("whatsapp.greeting"));
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={t("whatsapp.fab")}
      className="fixed bottom-5 end-5 z-40 grid h-14 w-14 place-items-center rounded-full bg-[#25D366] text-white shadow-lg transition hover:scale-105"
      data-testid="whatsapp-fab"
    >
      <WhatsAppIcon />
    </a>
  );
}
