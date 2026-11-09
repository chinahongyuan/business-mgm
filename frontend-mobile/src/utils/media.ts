/** Additive API contract. Missing derivatives always fall back to the original. */
export type MediaVariant = { url: string; width: number; height: number; bytes: number };
export type MediaAsset = {
  original: string;
  width: number;
  height: number;
  images?: MediaVariant[];
  poster?: string;
  videos?: (MediaVariant & { label: string })[];
};
export type MediaMap = Record<string, MediaAsset | null>;

export function imageSrcset(media?: MediaAsset | null, maxWidth = 1080): string {
  return (media?.images || [])
    .filter((image) => image.width > 0 && image.width <= maxWidth)
    .map((image) => `${image.url} ${image.width}w`)
    .join(", ");
}
