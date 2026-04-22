/** 移动端用户 BD-09 坐标本地缓存，减少重复定位（如多次点击「位置」排序） */

const STORAGE_KEY = "bmgm_user_geo_bd09";
const TTL_MS = 10 * 60 * 1000;

type Stored = { lat: number; lng: number; ts: number };

function safeParse(raw: string | null): Stored | null {
  if (!raw) return null;
  try {
    const o = JSON.parse(raw) as unknown;
    if (
      typeof o === "object" &&
      o !== null &&
      "lat" in o &&
      "lng" in o &&
      "ts" in o &&
      typeof (o as Stored).lat === "number" &&
      typeof (o as Stored).lng === "number" &&
      typeof (o as Stored).ts === "number" &&
      Number.isFinite((o as Stored).lat) &&
      Number.isFinite((o as Stored).lng)
    ) {
      return o as Stored;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function getCachedGeo(): { lat: number; lng: number } | null {
  if (typeof localStorage === "undefined") return null;
  const s = safeParse(localStorage.getItem(STORAGE_KEY));
  if (!s) return null;
  if (Date.now() - s.ts > TTL_MS) {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
  return { lat: s.lat, lng: s.lng };
}

export function setCachedGeo(lat: number, lng: number): void {
  if (typeof localStorage === "undefined") return;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
  try {
    const payload: Stored = { lat, lng, ts: Date.now() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota / private mode */
  }
}

export function clearCachedGeo(): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
