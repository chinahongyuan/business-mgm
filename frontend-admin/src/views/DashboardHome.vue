<template>
  <div class="dash">
    <header class="dash-hero">
      <div class="dash-hero__main">
        <h1 class="dash-hero__title">商品概览</h1>
      </div>
      <div class="dash-hero__aside" aria-live="polite">
        <span class="dash-hero__date">{{ todayLabel }}</span>
      </div>
    </header>

    <section class="dash-block" aria-label="核心指标">
      <div class="metric-grid">
        <div
          v-for="(k, index) in kpis"
          :key="k.label"
          class="metric-tile"
        >
          <div class="metric-tile__top">
            <span class="metric-tile__icon" aria-hidden="true">
              <el-icon :size="22">
                <component :is="kpiIcons[index % kpiIcons.length]" />
              </el-icon>
            </span>
            <span class="metric-tile__label">{{ k.label }}</span>
          </div>
          <div v-if="k.hint" class="metric-tile__hint">{{ k.hint }}</div>
          <div class="metric-tile__value">
            <span class="metric-tile__num">{{ formatKpiValue(k) }}</span>
            <span class="metric-tile__suffix">{{ k.suffix }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="dash-block dash-block--chart" aria-label="区域商品分布">
      <div class="chart-panel">
        <div class="chart-panel__head">
          <div class="chart-panel__titles">
            <h2 class="chart-panel__title">区域分布情况</h2>
            <p class="chart-panel__sub">
              按商品「所属区域」汇总上架与下架数量；并列柱形便于对比区域结构
            </p>
          </div>
          <el-tag class="chart-panel__tag" type="info" effect="plain" size="small">维度 · 区域</el-tag>
        </div>
        <div class="chart-panel__canvas">
          <VChart class="chart-region" :option="regionBarOption" autoresize />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { BarChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  Calendar,
  CircleCheck,
  CircleClose,
  Goods,
  Hide,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import VChart from "vue-echarts";

import { http } from "@/api/http";
import { useThemeStore } from "@/store/theme";

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent]);

const { isDark } = storeToRefs(useThemeStore());

/** 顺序与接口返回的 kpis 一致 */
const kpiIcons = [Goods, CircleCheck, CircleClose, Hide, Calendar, User] as const;

type Kpi = {
  label: string;
  value: number;
  suffix: string;
  hint?: string;
  isDecimal?: boolean;
};

type Summary = {
  kpis: Kpi[];
  regionStats: { labels: string[]; onShelf: number[]; offShelf: number[] };
};

const summary = ref<Summary | null>(null);

const kpis = computed(() => summary.value?.kpis || []);

const todayLabel = computed(() => {
  const d = new Date();
  return d.toLocaleDateString("zh-CN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
});

function formatKpiValue(k: Kpi): string {
  if (k.isDecimal) {
    return Number(k.value).toFixed(1);
  }
  return String(k.value ?? 0);
}

const regionBarOption = computed(() => {
  const s = summary.value?.regionStats;
  const labels = s?.labels || [];
  const onData = s?.onShelf || [];
  const offData = s?.offShelf || [];
  const empty = !labels.length;
  const dark = isDark.value;

  return {
    color: dark ? ["#2dd4bf", "#94a3b8"] : ["#0d9488", "#64748b"],
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
        shadowStyle: { color: dark ? "rgba(148,163,184,0.12)" : "rgba(15,23,42,0.06)" },
      },
      backgroundColor: dark ? "rgba(15,23,42,0.96)" : "rgba(255,255,255,0.98)",
      borderColor: dark ? "rgba(148,163,184,0.22)" : "rgba(15,23,42,0.06)",
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: dark ? "#e2e8f0" : "#0f172a", fontSize: 13 },
      extraCssText: dark
        ? "box-shadow: 0 8px 32px rgba(0,0,0,0.45); border-radius: 8px;"
        : "box-shadow: 0 8px 32px rgba(15,23,42,0.1); border-radius: 8px;",
    },
    legend: {
      top: 0,
      left: "center",
      itemGap: 28,
      itemWidth: 8,
      itemHeight: 8,
      icon: "roundRect",
      textStyle: {
        color: dark ? "rgba(226,232,240,0.72)" : "rgba(15,23,42,0.65)",
        fontSize: 12,
      },
    },
    xAxis: {
      type: "category",
      data: empty ? ["暂无数据"] : labels,
      axisLine: {
        lineStyle: { color: dark ? "rgba(148,163,184,0.2)" : "rgba(15,23,42,0.07)" },
      },
      axisTick: { show: false },
      axisLabel: {
        color: dark ? "rgba(226,232,240,0.62)" : "rgba(15,23,42,0.58)",
        interval: 0,
        rotate: labels.length > 7 ? 24 : 0,
        fontSize: 12,
      },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: {
        lineStyle: { color: dark ? "rgba(148,163,184,0.12)" : "rgba(15,23,42,0.06)" },
      },
      axisLabel: {
        color: dark ? "rgba(148,163,184,0.75)" : "rgba(15,23,42,0.45)",
        fontSize: 11,
      },
    },
    animationDuration: 420,
    animationEasing: "cubicOut",
    series: empty
      ? [
          {
            name: "上架",
            type: "bar",
            data: [0],
            itemStyle: {
              color: "rgba(148,163,184,0.25)",
              borderRadius: [4, 4, 0, 0],
            },
          },
        ]
      : [
          {
            name: "上架",
            type: "bar",
            data: onData,
            barGap: "18%",
            barMaxWidth: 32,
            itemStyle: { borderRadius: [4, 4, 0, 0] },
            emphasis: { focus: "series" },
          },
          {
            name: "下架",
            type: "bar",
            data: offData,
            barMaxWidth: 32,
            itemStyle: { borderRadius: [4, 4, 0, 0] },
            emphasis: { focus: "series" },
          },
        ],
  };
});

onMounted(async () => {
  try {
    const { data } = await http.get("/dashboard/summary");
    summary.value = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载概览失败");
  }
});
</script>

<style scoped>
/* 典型经营看板：页眉锚点 → 指标磁贴带 → 主图区（画布与标题分离） */
.dash {
  max-width: 1320px;
  margin: 0 auto;
  padding: 4px 4px 32px;
}

@media (min-width: 900px) {
  .dash {
    padding: 8px 16px 40px;
  }
}

.dash-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 24px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.dash-hero__title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #0f172a;
}

.dash-hero__desc {
  margin: 0;
  max-width: 36em;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(15, 23, 42, 0.48);
}

.dash-hero__aside {
  flex-shrink: 0;
}

.dash-hero__date {
  display: inline-block;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: rgba(15, 23, 42, 0.55);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset;
}

.dash-block {
  margin-bottom: 24px;
}

.dash-block--chart {
  margin-bottom: 0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.metric-tile {
  position: relative;
  padding: 18px 18px 20px;
  border-radius: var(--bm-radius, 12px);
  border: var(--bm-border);
  background: #fff;
  box-shadow: var(--bm-shadow);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.metric-tile:hover {
  border-color: rgba(37, 99, 235, 0.18);
  box-shadow:
    0 10px 30px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(37, 99, 235, 0.06);
}

.metric-tile__top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.metric-tile__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  color: #2563eb;
  background: linear-gradient(145deg, rgba(37, 99, 235, 0.1) 0%, rgba(124, 58, 237, 0.06) 100%);
}

.metric-tile__label {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgba(15, 23, 42, 0.55);
  line-height: 1.35;
}

.metric-tile__hint {
  margin-top: 4px;
  font-size: 11px;
  color: rgba(15, 23, 42, 0.38);
}

.metric-tile__value {
  margin-top: 14px;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 6px;
}

.metric-tile__num {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.metric-tile__suffix {
  font-size: 13px;
  font-weight: 500;
  color: rgba(15, 23, 42, 0.4);
}

.chart-panel {
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  background: #fff;
  box-shadow: var(--bm-shadow);
  overflow: hidden;
}

.chart-panel__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 20px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.65) 0%, #fff 100%);
}

.chart-panel__title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.chart-panel__sub {
  margin: 0;
  max-width: 48em;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(15, 23, 42, 0.45);
}

.chart-panel__tag {
  flex-shrink: 0;
  border-radius: 999px !important;
  font-weight: 500;
}

.chart-panel__canvas {
  padding: 12px 16px 20px;
  background: #f8fafc;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
}

.chart-region {
  width: 100%;
  height: min(400px, 50vh);
  min-height: 280px;
}
</style>