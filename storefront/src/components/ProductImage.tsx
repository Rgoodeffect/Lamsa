import Image, { type ImageProps } from "next/image";

import { mediaUrl } from "@/lib/env";

type Props = Omit<ImageProps, "src"> & { src: string | null | undefined };

/** next/image for ERPNext file paths; falls back to a brand placeholder. */
export function ProductImage({ src, alt, ...props }: Props) {
  const url = mediaUrl(src) ?? "/placeholder.svg";
  return <Image src={url} alt={alt} {...props} />;
}
