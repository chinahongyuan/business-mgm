<template>
  <div v-loading="loading" class="stats-screen" :class="{ 'stats-screen--light': !isDark }">
    <header class="stats-screen__hero">
      <div>
        <h1 class="stats-screen__title">活跃度统计</h1>
        <p class="stats-screen__sub">
          围绕移动端用户行为与互动数据：新增用户、日活（按最后活跃时间）、留言量近 30 日趋势；并依据「最新登录时间」汇总
          24 小时访问时段分布，支撑运营评估拉新、留存与推广时段。
        </p>
      </div>
    </header>

    <section v-if="kpis.length" class="stats-kpi">
      <div v-for="k in kpis" :key="k.label" class="stats-kpi__card">
        <div class="stats-kpi__label">{{ k.label }}</div>
        <div>
          <span class="stats-kpi__value">{{ formatKpi(k) }}</span>
          <span class="stats-kpi__suffix">{{ k.suffix }}</span>
        </div>
      </div>
    </section>

    <div class="stats-grid">
      <section class="stats-panel stats-panel--third">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">新增用户（30 日）</h2>
          <p class="stats-panel__hint">按注册日</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optNew" autoresize />
      </section>
      <section class="stats-panel stats-panel--third">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">活跃用户数（30 日）</h2>
          <p class="stats-panel__hint">当日有访问的用户数</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optActive" autoresize />
      </section>
      <section class="stats-panel stats-panel--third">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">留言提交量（30 日）</h2>
          <p class="stats-panel__hint">商品留言创建量</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optMsg" autoresize />
      </section>

      <section class="stats-panel">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">登录时段分布</h2>
          <p class="stats-panel__hint">
            以每位用户最近一次「登录时间」所在小时统计（UTC）；{{ loginMetaHint }}
          </p>
        </div>
        <VChart class="stats-chart stats-chart--tall" :option="optLoginHour" autoresize />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import VChart from "vue-echarts";

import { http } from "@/api/http";
import { useThemeStore } from "@/store/theme";
import { STATS_PALETTE, chartTheme } from "@/utils/statsChartTheme";

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent]);

const { isDark } = storeToRefs(useThemeStore());
const loading = ref(false);
const payload = ref<{
  kpis: { label: string; value: number; suffix: string; isDecimal?: boolean }[];
  newUsersByDay: { labels: string[]; values: number[] };
  activeUsersByDay: { labels: string[]; values: number[] };
  messagesByDay: { labels: string[]; values: number[] };
  loginHourDistribution?: {
    labels: string[];
    values: number[];
    meta?: { timezoneNote?: string; usersWithoutLogin?: number };
  };
} | null>(null);

const kpis = computed(() => payload.value?.kpis || []);

const loginMetaHint = computed(() => {
  const m = payload.value?.loginHourDistribution?.meta;
  const n = m?.usersWithoutLogin ?? 0;
  if (n > 0) return `无登录记录用户 ${n} 人未计入柱状图。`;
  return "全部用户均有登录记录。";
});

function formatKpi(k: { value: number; suffix: string; isDecimal?: boolean }) {
  if (k.isDecimal) return Number(k.value).toFixed(1);
  return String(k.value ?? 0);
}

function lineOption(
  labels: string[],
  values: number[],
  color: string,
  name: string,
  dark: boolean,
) {
  const t = chartTheme(dark);
  return {
    color: [color],
    tooltip: {
      trigger: "axis",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 8, top: 28, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.textMuted, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    series: [
      {
        name,
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        data: values,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
      },
    ],
  };
}

const optNew = computed(() => {
  const p = payload.value?.newUsersByDay;
  const dark = isDark.value;
  if (!p) return lineOption([], [], STATS_PALETTE[0], "新增", dark);
  return lineOption(p.labels, p.values, STATS_PALETTE[0], "新增用户", dark);
});

const optActive = computed(() => {
  const p = payload.value?.activeUsersByDay;
  const dark = isDark.value;
  if (!p) return lineOption([], [], STATS_PALETTE[1], "活跃", dark);
  return lineOption(p.labels, p.values, STATS_PALETTE[1], "活跃用户", dark);
});

const optMsg = computed(() => {
  const p = payload.value?.messagesByDay;
  const dark = isDark.value;
  if (!p) return lineOption([], [], STATS_PALETTE[2], "留言", dark);
  return lineOption(p.labels, p.values, STATS_PALETTE[2], "留言", dark);
});

function barHourOption(labels: string[], values: number[], dark: boolean) {
  const t = chartTheme(dark);
  return {
    color: [STATS_PALETTE[3]],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 8, top: 28, bottom: 8, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.textMuted, fontSize: 10, rotate: 40, interval: 0 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    series: [
      {
        name: "用户数",
        type: "bar",
        data: values,
        barMaxWidth: 20,
        itemStyle: {
          borderRadius: [5, 5, 0, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(251, 191, 36, 0.95)" },
              { offset: 1, color: "rgba(245, 158, 11, 0.35)" },
            ],
          },
        },
      },
    ],
  };
}

const optLoginHour = computed(() => {
  const p = payload.value?.loginHourDistribution;
  const dark = isDark.value;
  if (!p?.labels?.length) return barHourOption([], [], dark);
  return barHourOption(p.labels, p.values, dark);
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/stats/activity");
    payload.value = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
