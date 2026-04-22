/**
 * 获取用户 BD-09 坐标（与商户后台百度选点一致）。
 *
 * 定位策略：
 * 1. 百度地图定位（需要 AK）
 * 2. 浏览器定位
 * 3. IP 网络定位（兜底）
 */

import { getCachedGeo, setCachedGeo } from "@/utils/geoCache";
import { wgs84ToBd09 } from "@/utils/coordTransform";
import { getBaiduGeoPosition } from "@/utils/baiduGeo";

export type GeoRequestResult = {
  success: boolean;
  permissionDenied?: boolean;
  lat?: number;
  lng?: number;
  hint?: string;
  /** 为 true 表示来自本地缓存（默认 10 分钟内有效） */
  fromCache?: boolean;
};

type BrowserTry =
  | { ok: true; lat: number; lng: number }
  | { ok: false; permissionDenied: boolean; hint: string };

type BaiduTry =
  | { ok: true; lat: number; lng: number }
  | { ok: false; error: string };

async function tryBaiduGeo(baiduAk: string): Promise<BaiduTry> {
  console.log("[Geo] 尝试百度地图定位...");
  if (!baiduAk || !baiduAk.trim()) {
    return { ok: false, error: "百度定位：未配置 AK" };
  }
  try {
    const pos = await getBaiduGeoPosition(baiduAk.trim());
    console.log("[Geo] 百度定位成功:", pos.lat, pos.lng);
    return { ok: true, lat: pos.lat, lng: pos.lng };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.log("[Geo] 百度定位失败:", msg);
    if (msg.includes("AK") || msg.includes("ak")) {
      return { ok: false, error: "百度定位：AK 无效" };
    }
    if (msg.includes("超时")) {
      return { ok: false, error: "百度定位超时" };
    }
    if (msg.includes("权限") || msg.includes("permission")) {
      return { ok: false, error: "百度定位失败：权限错误" };
    }
    return { ok: false, error: `百度定位失败：${msg}` };
  }
}

async function tryBrowserBd09(): Promise<BrowserTry> {
  console.log("[Geo] 尝试浏览器定位...");
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      resolve({ ok: false, permissionDenied: false, hint: "当前环境不支持浏览器定位" });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        console.log("[Geo] 浏览器定位成功:", pos.coords.latitude, pos.coords.longitude);
        const bd = wgs84ToBd09(pos.coords.latitude, pos.coords.longitude);
        resolve({ ok: true, lat: bd.lat, lng: bd.lng });
      },
      (err: GeolocationPositionError) => {
        console.log("[Geo] 浏览器定位失败:", err.code, err.message);
        const denied = err.code === 1;
        let hint = "浏览器定位失败";
        if (denied) hint = "已拒绝浏览器定位权限";
        else if (err.code === 3) hint = "浏览器定位超时";
        else if (err.code === 2) hint = "浏览器暂时无法获取位置";
        resolve({ ok: false, permissionDenied: denied, hint });
      },
      {
        enableHighAccuracy: false,
        maximumAge: 0,
        timeout: 10000,
      },
    );
  });
}

async function tryThirdPartyIpGeo(): Promise<{ lat: number; lng: number } | null> {
  const ipApiServices = [
    {
      url: "https://ipapi.co/json/",
      parser: (data: Record<string, unknown>) => ({
        lat: data.latitude,
        lng: data.longitude,
      }),
    },
    {
      url: "http://ip-api.com/json/",
      parser: (data: Record<string, unknown>) => ({
        lat: data.lat,
        lng: data.lon,
      }),
    },
  ];

  for (const service of ipApiServices) {
    try {
      console.log("[Geo] 尝试 IP 定位:", service.url);
      const response = await fetch(service.url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const loc = service.parser(data);
      if (loc.lat && loc.lng) {
        console.log("[Geo] IP 定位成功:", loc);
        const bd = wgs84ToBd09(Number(loc.lat), Number(loc.lng));
        return { lat: bd.lat, lng: bd.lng };
      }
    } catch (e) {
      console.error("[Geo] IP 定位失败:", service.url, e);
    }
  }
  return null;
}

export async function requestUserGeo(options: {
  baiduAk?: string;
  /** 为 true 时跳过本地缓存，强制重新定位（如帮助内「重试」） */
  forceRefresh?: boolean;
}): Promise<GeoRequestResult> {
  if (!options.forceRefresh) {
    const cached = getCachedGeo();
    if (cached) {
      return {
        success: true,
        lat: cached.lat,
        lng: cached.lng,
        hint: "已使用近期定位（10 分钟内）",
        fromCache: true,
      };
    }
  }

  /** 定位优先级：1. 百度定位 → 2. 浏览器定位 → 3. IP网络定位 */

  /** 1. 尝试百度地图定位 */
  if (options.baiduAk) {
    const baiduResult = await tryBaiduGeo(options.baiduAk);
    if (baiduResult.ok) {
      setCachedGeo(baiduResult.lat, baiduResult.lng);
      return {
        success: true,
        lat: baiduResult.lat,
        lng: baiduResult.lng,
        hint: "已使用百度定位",
        fromCache: false,
      };
    }
    /** 百度定位失败，继续尝试浏览器定位 */
  }

  /** 2. 尝试浏览器定位 */
  const browserResult = await tryBrowserBd09();
  if (browserResult.ok) {
    setCachedGeo(browserResult.lat, browserResult.lng);
    return {
      success: true,
      lat: browserResult.lat,
      lng: browserResult.lng,
      hint: "已使用本机定位",
      fromCache: false,
    };
  }

  /** 3. 尝试 IP 网络定位（兜底） */
  const ipResult = await tryThirdPartyIpGeo();
  if (ipResult) {
    setCachedGeo(ipResult.lat, ipResult.lng);
    return {
      success: true,
      lat: ipResult.lat,
      lng: ipResult.lng,
      hint: "已使用网络定位",
      fromCache: false,
    };
  }

  /** 全部定位失败 */
  if (browserResult.permissionDenied) {
    return {
      success: false,
      permissionDenied: true,
      hint: "已拒绝浏览器定位权限；请在系统设置中允许定位",
    };
  }

  return {
    success: false,
    permissionDenied: false,
    hint: "无法获取位置；请检查网络或开启定位权限",
  };
}

