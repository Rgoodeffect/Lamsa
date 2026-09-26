/** wa.me link with a prefilled message. `number` is digits only, e.g. 218912345678. */
export function whatsappLink(number: string | null | undefined, message?: string): string | null {
  if (!number) return null;
  const text = message ? `?text=${encodeURIComponent(message)}` : "";
  return `https://wa.me/${number.replace(/\D/g, "")}${text}`;
}
