import { reactive } from "vue";

const STORAGE_PREFIX = "bmgm-admin:table-col-widths:";

export type ColWidthPreset = { width?: number; minWidth?: number };

function sanitizeWidths(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== "object") return {};
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    const n = Number(v);
    if (Number.isFinite(n) && n >= 40) out[k] = Math.round(n);
  }
  return out;
}

function loadFromStorage(tableId: string): Record<string, number> {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + tableId);
    if (!raw) return {};
    return sanitizeWidths(JSON.parse(raw));
  } catch {
    return {};
  }
}

function saveToStorage(tableId: string, widths: Record<string, number>) {
  try {
    localStorage.setItem(STORAGE_PREFIX + tableId, JSON.stringify(widths));
  } catch {
    /* quota / private mode */
  }
}

/**
 * 管理后台表格列宽本地记忆：拖动表头分隔线后写入 localStorage，下次进入同一列表恢复。
 * 需在每列设置稳定的 column-key，并在 el-table 上监听 @header-dragend。
 */
export function usePersistedTableWidths(tableId: string) {
  const widths = reactive<Record<string, number>>(loadFromStorage(tableId));

  function persist() {
    saveToStorage(tableId, { ...widths });
  }

  /** 绑定到 el-table-column：有记忆宽度时固定 width，否则使用预设 width / minWidth */
  function col(key: string, preset: ColWidthPreset) {
    const s = widths[key];
    if (s != null && s > 0) {
      return { width: s, minWidth: undefined as number | undefined };
    }
    return {
      width: preset.width,
      minWidth: preset.minWidth,
    };
  }

  function onHeaderDragEnd(
    newWidth: number,
    _oldWidth: number,
    column: { columnKey?: string; property?: string; label?: string }
  ) {
    const k = column.columnKey || (column.property != null ? String(column.property) : "");
    if (!k) return;
    const w = Math.max(40, Math.round(Number(newWidth) || 0));
    if (!Number.isFinite(w)) return;
    widths[k] = w;
    persist();
  }

  return { col, onHeaderDragEnd };
}
