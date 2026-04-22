/**
 * WGS84 → GCJ-02 → BD-09，与商户后台百度地图选点坐标系一致，便于与商品经纬度算距。
 * 算法参考常见 coordtransform 实现。
 */

const PI = Math.PI;

function outOfChina(lng: number, lat: number): boolean {
  return lat < 0.8293 || lat > 55.8271 || lng < 72.004 || lng > 137.8347;
}

function transformLat(lng: number, lat: number): number {
  let ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng));
  ret += ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0;
  ret += ((20.0 * Math.sin(lat * PI) + 40.0 * Math.sin((lat / 3.0) * PI)) * 2.0) / 3.0;
  ret += ((160.0 * Math.sin((lat / 12.0) * PI) + 320 * Math.sin((lat * PI) / 30.0)) * 2.0) / 3.0;
  return ret;
}

function transformLng(lng: number, lat: number): number {
  let ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng));
  ret += ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0;
  ret += ((20.0 * Math.sin(lng * PI) + 40.0 * Math.sin((lng / 3.0) * PI)) * 2.0) / 3.0;
  ret += ((150.0 * Math.sin((lng / 12.0) * PI) + 300.0 * Math.sin((lng / 30.0) * PI)) * 2.0) / 3.0;
  return ret;
}

function wgs84ToGcj02(lat: number, lng: number): [number, number] {
  if (outOfChina(lng, lat)) return [lat, lng];
  const a = 6378245.0;
  const ee = 0.00669342162296594323;
  let dlat = transformLat(lng - 105.0, lat - 35.0);
  let dlng = transformLng(lng - 105.0, lat - 35.0);
  const radlat = (lat / 180.0) * PI;
  let magic = Math.sin(radlat);
  magic = 1 - ee * magic * magic;
  const sqrtmagic = Math.sqrt(magic);
  dlat = (dlat * 180.0) / (((a * (1 - ee)) / (magic * sqrtmagic)) * PI);
  dlng = (dlng * 180.0) / ((a / sqrtmagic) * Math.cos(radlat) * PI);
  const mglat = lat + dlat;
  const mglng = lng + dlng;
  return [mglat, mglng];
}

function gcj02ToBd09(lat: number, lng: number): [number, number] {
  const z = Math.sqrt(lng * lng + lat * lat) + 0.00002 * Math.sin(lat * PI * 3000.0 / 180.0);
  const theta = Math.atan2(lat, lng) + 0.000003 * Math.cos(lng * PI * 3000.0 / 180.0);
  const bdLng = z * Math.cos(theta) + 0.0065;
  const bdLat = z * Math.sin(theta) + 0.006;
  return [bdLat, bdLng];
}

/** 浏览器 WGS84 经纬度 → 百度 BD-09，与商品表坐标一致 */
export function wgs84ToBd09(lat: number, lng: number): { lat: number; lng: number } {
  const [gcjLat, gcjLng] = wgs84ToGcj02(lat, lng);
  const [bdLat, bdLng] = gcj02ToBd09(gcjLat, gcjLng);
  return { lat: bdLat, lng: bdLng };
}
