<template>
  <div class="bm-map-wrap">
    <el-alert
      v-if="!ak"
      type="warning"
      show-icon
      :closable="false"
      title="未配置百度地图 AK（前端不会请求 api.map.baidu.com）"
      description="请确认后端已加载含 baidu_map.ak 的 config.json 并重启服务；在开发者工具 Network 中查看 /api/public/config 返回的 baiduMapAk 是否非空。"
    />
    <template v-else>
      <el-alert v-if="loadError" type="error" show-icon :closable="false" :title="loadError" class="bm-map-err" />
      <div ref="mapContainer" class="bm-map-canvas" role="application" aria-label="百度地图选点" />
      <div class="bm-map-hint">
        地图点击选点会同步经纬度与行政区；商品地址在下方「经纬度」之后填写，输入关键字可查看南京市范围内预选，点选某条后写入地址。
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  ak: string;
  province: string;
  city: string;
  district: string;
  longitude: number | null;
  latitude: number | null;
}>();

const emit = defineEmits<{
  "update:province": [v: string];
  "update:city": [v: string];
  "update:district": [v: string];
  "update:longitude": [v: number | null];
  "update:latitude": [v: number | null];
  "update:address": [v: string];
}>();

export type MapPoiSuggestion = {
  title: string;
  address: string;
  lng: number;
  lat: number;
};

const mapContainer = ref<HTMLElement | null>(null);
const loadError = ref("");

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let map: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let marker: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let geocoder: any = null;

let booting = false;
let suggestionReq = 0;
/** 自定义滚轮：始终拦截滚轮事件，有选点时以选点为中心，无选点时以鼠标为中心 */
let wheelHandler: ((e: WheelEvent) => void) | null = null;

function bmap(): any {
  return (window as unknown as { BMap?: unknown }).BMap;
}

function waitForBMap(maxMs = 15000): Promise<void> {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    const id = window.setInterval(() => {
      if (bmap()) {
        window.clearInterval(id);
        resolve();
      } else if (Date.now() - t0 > maxMs) {
        window.clearInterval(id);
        reject(new Error("百度地图 API 未就绪（可检查 AK 类型、网络或 Referer）"));
      }
    }, 50);
  });
}

function loadScript(ak: string): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (bmap()) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const tagId = "bm-baidu-map-script";
    const stale = document.getElementById(tagId);
    if (stale && !bmap()) {
      stale.remove();
    }
    if (bmap()) {
      resolve();
      return;
    }

    const cbName = `__bm_cb_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
    const w = window as unknown as Record<string, unknown>;
    let settled = false;

    const done = (ok: boolean, err?: Error) => {
      if (settled) return;
      settled = true;
      try {
        delete w[cbName];
      } catch {
        /* ignore */
      }
      if (ok) resolve();
      else reject(err ?? new Error("百度地图初始化失败"));
    };

    const timer = window.setTimeout(() => {
      done(false, new Error("百度地图加载超时（请检查网络或 AK）"));
    }, 20000);

    w[cbName] = () => {
      window.clearTimeout(timer);
      if (bmap()) {
        done(true);
        return;
      }
      waitForBMap(8000)
        .then(() => done(true))
        .catch((e) => done(false, e instanceof Error ? e : new Error(String(e))));
    };

    const src = `https://api.map.baidu.com/api?v=3.0&ak=${encodeURIComponent(ak)}&callback=${cbName}`;
    if (import.meta.env.DEV) {
      console.debug("[BaiduMapRegion] 使用 callback 异步加载（避免 document.write 在 SPA 中失效）", src);
    }
    const s = document.createElement("script");
    s.id = tagId;
    s.src = src;
    s.onerror = () => {
      window.clearTimeout(timer);
      done(false, new Error("无法加载百度地图脚本（网络或 CSP）"));
    };
    document.head.appendChild(s);
  });
}

function setMarkerAt(lng: number, lat: number) {
  const B = bmap();
  if (!map || !B) return;
  const pt = new B.Point(lng, lat);
  if (!marker) {
    marker = new B.Marker(pt);
    map.addOverlay(marker);
  } else {
    marker.setPosition(pt);
  }
  map.panTo(pt);
  updateWheelZoomBehavior();
}

/**
 * 自定义滚轮：
 * - 有选点时：围绕选点缩放（避免选点跑出视野）
 * - 无选点时：围绕鼠标位置缩放（百度默认滚轮不锚定鼠标）
 */
function updateWheelZoomBehavior() {
  if (!map) return;
  const el = typeof map.getContainer === "function" ? map.getContainer() : null;
  if (el && wheelHandler) {
    el.removeEventListener("wheel", wheelHandler, { capture: true });
    wheelHandler = null;
  }

  wheelHandler = (e: WheelEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!map) return;

    const rect = el?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (marker) {
      const pt = marker.getPosition?.();
      if (pt) {
        map.setCenter(pt);
      }
    } else {
      const mousePoint = map.pixelToPoint(new (bmap().Pixel)(mouseX, mouseY));
      map.setCenter(mousePoint);
    }

    if (e.deltaY < 0) {
      map.zoomIn();
    } else {
      map.zoomOut();
    }
  };

  if (el) {
    el.addEventListener("wheel", wheelHandler, { passive: false, capture: true });
  }
}

type GeocodeRs = {
  address?: string;
  business?: string;
  /** 百度常见字段名（拼写如此） */
  sematic_description?: string;
  addressComponents?: {
    province?: string;
    city?: string;
    district?: string;
    street?: string;
    streetNumber?: string;
  };
  surroundingPois?: Array<{
    title?: string;
    address?: string;
    distance?: number;
  }>;
};

/** 从逆地理结果中拼出尽量详细的展示地址（优先语义描述、再比选周边 POI 中更长的地址、再补道路门牌） */
function buildBestAddressFromGeocode(r: GeocodeRs): string {
  const c = r.addressComponents || {};
  const sem =
    (typeof r.sematic_description === "string" && r.sematic_description.trim()) ||
    (typeof (r as { sematicDescription?: string }).sematicDescription === "string" &&
      (r as { sematicDescription?: string }).sematicDescription?.trim()) ||
    "";
  if (sem) return sem;

  const base = (r.address || "").trim();
  const streetLine = [c.street, c.streetNumber].filter(Boolean).join("");
  let out = base;
  if (streetLine && base && !base.includes(streetLine)) {
    out = `${base}${streetLine}`;
  } else if (streetLine && !base) {
    out = [c.province, c.city, c.district, streetLine].filter(Boolean).join("");
  }

  const pois = r.surroundingPois;
  if (Array.isArray(pois) && pois.length > 0) {
    const sorted = [...pois].sort((a, b) => (a.distance ?? 999999) - (b.distance ?? 999999));
    for (const p of sorted.slice(0, 5)) {
      const pa = (p.address || "").trim();
      if (pa.length > out.length) {
        out = pa;
        break;
      }
    }
  }

  const bus = typeof r.business === "string" ? r.business.trim() : "";
  if (bus && out && !out.includes(bus)) {
    out = `${out} ${bus}`.trim();
  }

  return out || base;
}

/**
 * 逆地理编码：填充省市区；地址优先用 addressOverride（预选点选），否则用 buildBestAddressFromGeocode
 */
function applyReverse(pt: { lng: number; lat: number }, fillAddress = true, addressOverride?: string | null) {
  const B = bmap();
  if (!B) return;

  const geo = new B.Geocoder();
  const ptObj = new B.Point(pt.lng, pt.lat);
  const onResult = (rs: unknown) => {
    if (!rs || typeof rs !== "object") return;
    const r = rs as GeocodeRs;
    const c = r.addressComponents || {};
    const prov = c.province || "";
    const city = c.city || "";
    const dist = c.district || "";

    emit("update:province", prov);
    emit("update:city", city);
    emit("update:district", dist);
    emit("update:longitude", pt.lng);
    emit("update:latitude", pt.lat);
    if (!fillAddress) return;

    if (addressOverride != null && String(addressOverride).trim() !== "") {
      emit("update:address", String(addressOverride).trim());
      return;
    }
    const best = buildBestAddressFromGeocode(r);
    if (best) emit("update:address", best);
  };
  try {
    geo.getLocation(ptObj, onResult, { poiRadius: 300 });
  } catch {
    geo.getLocation(ptObj, onResult);
  }
}

function initMap() {
  const B = bmap();
  if (!props.ak || !mapContainer.value || !B) return;
  if (map) return;
  map = new B.Map(mapContainer.value);
  geocoder = new B.Geocoder();

  const lng = props.longitude;
  const lat = props.latitude;
  if (lng != null && lat != null && !Number.isNaN(Number(lng)) && !Number.isNaN(Number(lat))) {
    const pt = new B.Point(Number(lng), Number(lat));
    map.centerAndZoom(pt, 16);
    marker = new B.Marker(pt);
    map.addOverlay(marker);
  } else {
    map.centerAndZoom(new B.Point(118.796877, 32.060255), 12);
  }
  map.addEventListener("click", (e: { point: { lng: number; lat: number } }) => {
    const pt = e.point;
    setMarkerAt(pt.lng, pt.lat);
    applyReverse(pt, true, null);
  });

  updateWheelZoomBehavior();
}

async function bootstrap() {
  loadError.value = "";
  if (!props.ak?.trim()) {
    if (import.meta.env.DEV) {
      console.warn("[BaiduMapRegion] bootstrap 跳过：ak 为空（无 map.baidu 请求属正常）");
    }
    return;
  }
  if (map) return;
  if (booting) return;
  booting = true;
  try {
    await loadScript(props.ak);
    await nextTick();
    if (!mapContainer.value) await nextTick();
    if (!mapContainer.value) {
      loadError.value = "地图容器未挂载（异常），请刷新页面";
      return;
    }
    initMap();
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : "地图初始化失败";
  } finally {
    booting = false;
  }
}

onMounted(() => {
  void bootstrap();
});

watch(
  () => props.ak,
  () => {
    void bootstrap();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  if (map) {
    const el = typeof map.getContainer === "function" ? map.getContainer() : null;
    if (el && wheelHandler) {
      el.removeEventListener("wheel", wheelHandler, { capture: true });
    }
  }
  wheelHandler = null;
  map = null;
  marker = null;
  geocoder = null;
});

watch(
  () => [props.longitude, props.latitude],
  () => {
    if (!map || props.longitude == null || props.latitude == null) return;
    const lng = Number(props.longitude);
    const lat = Number(props.latitude);
    if (Number.isNaN(lng) || Number.isNaN(lat)) return;
    setMarkerAt(lng, lat);
  },
);

/** 根据地址文本定位地图并逆地理填充完整地址（保留给外部需要时调用；输入框不再自动调用） */
function searchAddress(address: string) {
  if (!map || !address.trim()) return;
  const B = bmap();
  if (!B) return;

  if (!geocoder) {
    geocoder = new B.Geocoder();
  }

  const city = props.city || props.province || "";
  geocoder.getPoint(
    address.trim(),
    (pt: { lng: number; lat: number } | null) => {
      if (pt) {
        map.centerAndZoom(pt, 16);
        setMarkerAt(pt.lng, pt.lat);
        applyReverse({ lng: pt.lng, lat: pt.lat }, true, null);
      }
    },
    city,
  );
}

/** 南京市大致范围（Bounds），用于 LocalSearch.searchInBounds */
function getNanjingBounds(B: any) {
  return new B.Bounds(new B.Point(118.32, 31.72), new B.Point(119.32, 32.48));
}

/** 关键词检索：仅在南京市范围内返回预选列表 */
function fetchPoiSuggestions(keyword: string): Promise<MapPoiSuggestion[]> {
  const B = bmap();
  const kw = keyword.trim();
  if (!map || !B || kw.length < 2) {
    return Promise.resolve([]);
  }
  const myReq = ++suggestionReq;
  const bounds = getNanjingBounds(B);
  return new Promise((resolve) => {
    const local = new B.LocalSearch(map, {
      onSearchComplete: (results: {
        getCurrentNumPois?: () => number;
        getNumPois?: () => number;
        getPoi?: (i: number) => {
          title?: string;
          address?: string;
          point?: { lng: number; lat: number };
        };
      }) => {
        if (myReq !== suggestionReq) return;
        const list: MapPoiSuggestion[] = [];
        try {
          const st = typeof local.getStatus === "function" ? local.getStatus() : -1;
          if (st !== 0) {
            resolve(list);
            return;
          }
          const n =
            typeof results.getCurrentNumPois === "function"
              ? results.getCurrentNumPois()
              : typeof results.getNumPois === "function"
                ? results.getNumPois()
                : 0;
          const max = Math.min(n, 10);
          for (let i = 0; i < max; i++) {
            const poi = results.getPoi?.(i);
            if (poi?.point && typeof poi.point.lng === "number" && typeof poi.point.lat === "number") {
              list.push({
                title: (poi.title || "").trim(),
                address: (poi.address || "").trim(),
                lng: poi.point.lng,
                lat: poi.point.lat,
              });
            }
          }
        } catch {
          /* ignore */
        }
        resolve(list);
      },
    });
    if (typeof local.searchInBounds === "function") {
      local.searchInBounds(kw, bounds);
    } else {
      local.search(`南京 ${kw}`);
    }
  });
}

/**
 * 定位到坐标；若传入 addressOverride（如点选预选的 POI 地址），则商品地址以该文案为准，否则用逆地理拼接
 */
function focusOnLngLat(lng: number, lat: number, addressOverride?: string | null) {
  const B = bmap();
  if (!map || !B) return;
  if (Number.isNaN(lng) || Number.isNaN(lat)) return;
  map.centerAndZoom(new B.Point(lng, lat), 16);
  setMarkerAt(lng, lat);
  applyReverse({ lng, lat }, true, addressOverride ?? null);
}

defineExpose({
  searchAddress,
  fetchPoiSuggestions,
  focusOnLngLat,
});
</script>

<style scoped>
.bm-map-wrap {
  width: 100%;
}

.bm-map-err {
  margin-bottom: 10px;
}

.bm-map-canvas {
  width: 66.67%;
  height: 624px;
  border-radius: var(--bm-radius, 12px);
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.12);
}

.bm-map-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(15, 23, 42, 0.55);
}
</style>
