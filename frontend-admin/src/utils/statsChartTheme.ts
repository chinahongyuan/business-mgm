/** 统计大屏 ECharts 与主题联动的颜色与通用配置 */

export const STATS_PALETTE = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#f472b6", "#22d3ee", "#fb7185", "#94a3b8"];

export function chartTheme(isDark: boolean) {
  return {
    text: isDark ? "#e2e8f0" : "#0f172a",
    textMuted: isDark ? "rgba(226,232,240,0.55)" : "rgba(15,23,42,0.55)",
    textWeak: isDark ? "rgba(148,163,184,0.75)" : "rgba(15,23,42,0.45)",
    splitLine: isDark ? "rgba(148,163,184,0.12)" : "rgba(15,23,42,0.06)",
    axisLine: isDark ? "rgba(148,163,184,0.2)" : "rgba(15,23,42,0.12)",
    tooltipBg: isDark ? "rgba(15,23,42,0.94)" : "rgba(255,255,255,0.96)",
    tooltipBorder: isDark ? "rgba(148,163,184,0.22)" : "rgba(15,23,42,0.08)",
  };
}
