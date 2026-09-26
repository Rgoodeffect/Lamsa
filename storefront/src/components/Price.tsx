import { formatPrice, formatPriceRange } from "@/lib/format";

export function Price({
  min,
  max,
  currency,
  className = "",
}: {
  min: number;
  max?: number;
  currency: string;
  className?: string;
}) {
  return (
    <span className={`font-semibold text-primary-700 ${className}`}>
      {max === undefined ? formatPrice(min, currency) : formatPriceRange(min, max, currency)}
    </span>
  );
}
