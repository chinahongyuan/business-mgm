/** 接口日期时间：后端存 naive UTC；JSON 可能为无时区 ISO。统一按 UTC 解析后格式化为本地 yyyy-MM-dd HH:mm:ss */

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** 将接口返回的 ISO 字符串解析为 Date（无时区后缀时视为 UTC，与后端 isoformat_utc 一致） */
export function parseServerDateTime(value: string | number | Date | null | undefined): Date {
  if (value instanceof Date) return value;
  if (value === null || value === undefined || value === "") return new Date(NaN);
  const raw = typeof value === "number" ? String(value) : String(value).trim();
  if (!raw) return new Date(NaN);
  if (/[zZ]$/.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw) || /[+-]\d{4}$/.test(raw)) {
    return new Date(raw);
  }
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(raw)) {
    const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
    return new Date(normalized.endsWith("Z") ? normalized : `${normalized}Z`);
  }
  return new Date(raw);
}

export function formatDateTime(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const d = parseServerDateTime(value);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}
