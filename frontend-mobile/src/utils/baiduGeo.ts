/** 动态加载百度地图 JS API，并用 BMap.Geolocation 取 BD-09 坐标（与后台商户坐标系一致）。 */

let scriptLoading: Promise<void> | null = null;

export function loadBaiduMapScript(ak: string): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("no window"));
  }
  const w = window as unknown as { BMap?: unknown };
  if (w.BMap) {
    return Promise.resolve();
  }
  if (!ak.trim()) {
    return Promise.reject(new Error("缺少百度地图 AK"));
  }
  if (scriptLoading) {
    return scriptLoading;
  }
  scriptLoading = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.async = true;
    s.src = `https://api.map.baidu.com/api?v=3.0&ak=${encodeURIComponent(ak.trim())}`;
    s.onload = () => resolve();
    s.onerror = () => {
      scriptLoading = null;
      reject(new Error("百度地图脚本加载失败"));
    };
    document.head.appendChild(s);
  });
  return scriptLoading;
}

type BMapGeoCtor = new () => {
  getCurrentPosition: (
    cb: (this: { getStatus: () => number }, r: { point?: { lat: number; lng: number } }) => void,
    opts?: { enableHighAccuracy?: boolean; maximumAge?: number; timeout?: number },
  ) => void;
};

/** 返回百度坐标系（BD-09）经纬度。 */
export async function getBaiduGeoPosition(ak: string): Promise<{ lat: number; lng: number }> {
  await loadBaiduMapScript(ak);
  const w = window as unknown as { BMap?: BMapGeoCtor; BMAP_STATUS_SUCCESS?: number };
  const BMap = w.BMap;
  if (!BMap) {
    throw new Error("BMap 未就绪");
  }
  const okStatus =
    typeof w.BMAP_STATUS_SUCCESS === "number" ? w.BMAP_STATUS_SUCCESS : 0;
  return new Promise((resolve, reject) => {
    const geo = new BMap.Geolocation();
    let settled = false;
    const timer = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error("百度定位超时"));
    }, 20000);
    geo.getCurrentPosition(
      function (
        this: { getStatus: () => number },
        r: { point?: { lat: number; lng: number } },
      ) {
        if (settled) return;
        window.clearTimeout(timer);
        try {
          const st = this.getStatus();
          if (st === okStatus && r?.point && Number.isFinite(r.point.lat) && Number.isFinite(r.point.lng)) {
            settled = true;
            resolve({ lat: r.point.lat, lng: r.point.lng });
          } else {
            settled = true;
            reject(new Error(`百度定位失败(status=${st})`));
          }
        } catch {
          settled = true;
          reject(new Error("百度定位异常"));
        }
      },
      { enableHighAccuracy: true, timeout: 18000, maximumAge: 60_000 },
    );
  });
}
